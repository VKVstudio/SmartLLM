#!/usr/bin/env python3
"""Single-Layer Qwen4Exp Streaming Runner for SmartLLM v2 (Wave 2 & Wave 3).

Streams donor Qwen3.8-Flash-Next one layer at a time with:
- Pure-PyTorch meta materialization (zero accelerate requirement).
- POSIX_FADV_DONTNEED shard page-cache eviction on every load.
- SafeStreamingPLENGramEmbedding on layer 1 (0 B persistent PLE RAM).
- Optional CuPyLinearPatch on dense projections when backend='cupy' under GPU_TOKEN.
- Exact non-MoE imatrix pre-hooks matching llama.cpp qwen4exp tensor names.
"""

from __future__ import annotations

import copy
import gc
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from scripts.v2.common_io import (
    DONOR_DIR,
    LayerImatrixCollector,
    QSAIndexerWrapper,
    ResumableFlatSequenceStore,
    SafetensorsIndex,
    SampleDomainFlags,
    SafeStreamingPLENGramEmbedding,
    classify_sample_domains,
    compute_position_embeddings_for_sample,
    free_submodule_to_meta,
    materialize_submodule,
    reorder_gdn_v_heads_activation,
)
from scripts.v2.cupy_moe_backend import (
    CuPyFastAttentionWrapper,
    CuPyGatedDeltaNetWrapper,
    CuPyLinearPatch,
    free_cupy_pools,
)


@dataclass
class PreparedSample:
    idx: int
    sample_id: str
    seq_len: int
    input_ids: torch.Tensor  # [1, S] int64 CPU
    mrope_position_ids: Optional[torch.Tensor]  # [3, 1, S] int64 CPU or None
    flags: SampleDomainFlags


def load_text_cfg_and_index(donor_dir: Path = DONOR_DIR) -> Tuple[Any, SafetensorsIndex]:
    from transformers import AutoConfig

    cfg = AutoConfig.from_pretrained(str(donor_dir), trust_remote_code=False)
    text_cfg = getattr(cfg, "text_config", cfg)
    text_cfg._attn_implementation = "sdpa"
    st_index = SafetensorsIndex(donor_dir, drop_cache=True)
    return text_cfg, st_index


def build_mtp_decoder_config(text_cfg: Any) -> Any:
    mtp_cfg = copy.deepcopy(text_cfg)
    mtp_cfg.num_hidden_layers = 1
    mtp_sub = getattr(text_cfg, "mtp", None) or {}
    mtp_ltypes = (
        mtp_sub.get("layer_types")
        if isinstance(mtp_sub, dict)
        else getattr(mtp_sub, "layer_types", None)
    )
    mtp_cfg.layer_types = list(mtp_ltypes) if mtp_ltypes else ["full_attention"]
    mtp_cfg.ple_layer_ids = []
    mtp_cfg._attn_implementation = "sdpa"
    return mtp_cfg


def _extract_record_image_path(rec: Dict[str, Any]) -> Optional[Path]:
    from scripts.v2.common_io import ROOT_DIR

    cand = rec.get("image_path") or rec.get("image")
    if not cand and isinstance(rec.get("images"), list) and rec["images"]:
        first = rec["images"][0]
        cand = first.get("path") if isinstance(first, dict) else first
    if not cand:
        return None
    p = Path(str(cand))
    if not p.is_absolute():
        p = ROOT_DIR / p
    return p if p.is_file() else None


def prepare_jsonl_samples_and_initial_states(
    jsonl_path: Path,
    e0_store_path: Optional[Path],
    h0_store_path: Path,
    donor_dir: Path = DONOR_DIR,
    max_samples: int = 0,
    max_seq_len: int = 2048,
    backend: str = "cpu",
    skip_embedding_init: bool = False,
    min_post_write_free_gib: float = 0.0,
) -> Tuple[List[PreparedSample], Optional[ResumableFlatSequenceStore], ResumableFlatSequenceStore]:
    """Tokenize JSONL dataset (including multimodal images if present), write optional E^(0)
    [1,S,1,D] and H^(0) [1,S,hc,D] stores sequentially with bounded RAM/VFS cache, and
    immediately free vision tower and embed_tokens.

    When `skip_embedding_init=True` (resume path), skips vision-tower forward and embed_tokens
    loading completely and opens existing `e0_store_path` / `h0_store_path` with `create=False`
    (asserting exact byte sizes on disk without overwriting slot files).
    """
    from PIL import Image
    from transformers import AutoImageProcessor, AutoTokenizer
    from transformers.models.qwen4_exp.modeling_qwen4_exp import (
        Qwen4ExpForConditionalGeneration,
        Qwen4ExpVisionModel,
    )

    full_cfg = AutoConfig_full(donor_dir)
    if hasattr(full_cfg, "vision_config"):
        full_cfg.vision_config._attn_implementation = "sdpa"
    text_cfg, st_index = load_text_cfg_and_index(donor_dir)
    hc_count = int(text_cfg.hc_count)
    hidden_size = int(text_cfg.hidden_size)
    pad_id = int(getattr(full_cfg, "image_token_id", 248056))

    raw_records: List[Dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw_records.append(json.loads(line))
            if max_samples > 0 and len(raw_records) >= max_samples:
                break

    has_any_vision = any(_extract_record_image_path(r) is not None for r in raw_records)

    tokenizer = AutoTokenizer.from_pretrained(str(donor_dir), trust_remote_code=False)
    img_processor = (
        AutoImageProcessor.from_pretrained(str(donor_dir), backend="pil")
        if has_any_vision
        else None
    )

    with torch.device("meta"):
        full_model = Qwen4ExpForConditionalGeneration._from_config(full_cfg)

    samples: List[PreparedSample] = []
    vis_batches: Dict[int, Dict[str, torch.Tensor]] = {}

    for idx, rec in enumerate(raw_records):
        flags = classify_sample_domains(rec)
        sid = str(rec.get("id") or rec.get("sample_id") or f"s_{idx:04d}")
        img_p = _extract_record_image_path(rec)
        mrope_pos: Optional[torch.Tensor] = None
        if img_p is not None and img_processor is not None:
            with Image.open(str(img_p)) as pil_im:
                img = pil_im.convert("RGB")
            img_out = img_processor(images=[img], return_tensors="pt")
            thw = img_out["image_grid_thw"].to(torch.int64).cpu()
            merge_sq = int(getattr(img_processor, "merge_size", 2)) ** 2
            n_vis_toks = int(thw[0].prod().item()) // merge_sq

            raw_txt = str(rec.get("text") or "")
            if not raw_txt:
                prompt_txt = str(rec.get("prompt") or "Analyze this UI design.")
                raw_txt = (
                    "<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>"
                    f"{prompt_txt}<|im_end|>\n<|im_start|>assistant\n"
                )
            elif "<|image_pad|>" not in raw_txt:
                raw_txt = f"<|vision_start|><|image_pad|><|vision_end|>\n{raw_txt}"

            if raw_txt.count("<|image_pad|>") == 1 and n_vis_toks > 1:
                expanded_txt = raw_txt.replace("<|image_pad|>", "<|image_pad|>" * n_vis_toks, 1)
            else:
                expanded_txt = raw_txt

            add_spec = not expanded_txt.startswith("<|im_start|>")
            enc = tokenizer(
                expanded_txt,
                return_tensors="pt",
                truncation=True,
                max_length=max_seq_len,
                add_special_tokens=add_spec,
            )
            ids = enc["input_ids"].to(torch.int64).cpu()
            if hasattr(full_model.model, "get_rope_index") and int((ids == pad_id).sum().item()) == n_vis_toks:
                mm_tt = (ids == pad_id).to(torch.int32)
                pos_ids, _ = full_model.model.get_rope_index(ids, mm_tt, image_grid_thw=thw)
                mrope_pos = pos_ids.to(torch.int64).cpu()
            if not skip_embedding_init:
                vis_batches[idx] = {
                    "pixel_values": img_out["pixel_values"].cpu(),
                    "image_grid_thw": thw,
                }
            del img_out
        else:
            if rec.get("text"):
                txt = str(rec["text"])
            elif "messages" in rec and isinstance(rec["messages"], list):
                txt = tokenizer.apply_chat_template(rec["messages"], tokenize=False, add_generation_prompt=False)
            else:
                txt = str(rec.get("prompt") or "")
            add_spec = not txt.startswith("<|im_start|>")
            enc = tokenizer(txt, return_tensors="pt", truncation=True, max_length=max_seq_len, add_special_tokens=add_spec)
            ids = enc["input_ids"].to(torch.int64).cpu()
            if ids.shape[1] < 2:
                ids = torch.cat([ids, torch.tensor([[int(tokenizer.eos_token_id or 0)]], dtype=torch.int64)], dim=1)

        samples.append(
            PreparedSample(
                idx=idx,
                sample_id=sid,
                seq_len=int(ids.shape[1]),
                input_ids=ids,
                mrope_position_ids=mrope_pos,
                flags=flags,
            )
        )

    del full_model, raw_records, tokenizer, img_processor
    gc.collect()

    seq_lengths = [s.seq_len for s in samples]
    if skip_embedding_init:
        del vis_batches
        e0_existing: Optional[ResumableFlatSequenceStore] = (
            ResumableFlatSequenceStore(
                e0_store_path, seq_lengths, hc_count=1, hidden_size=hidden_size, create=False
            )
            if e0_store_path is not None
            else None
        )
        h0_existing = ResumableFlatSequenceStore(
            h0_store_path, seq_lengths, hc_count=hc_count, hidden_size=hidden_size, create=False
        )
        return samples, e0_existing, h0_existing

    # Step 1: Process multimodal images FIRST (~66 MiB total output), then free vision tower completely
    vis_feats: Dict[int, torch.Tensor] = {}
    if vis_batches:
        vis_tower = Qwen4ExpVisionModel._from_config(full_cfg.vision_config).to(torch.bfloat16).eval()
        materialize_submodule(vis_tower, "model.visual", st_index, device="cpu")
        vis_patch = CuPyLinearPatch(vis_tower, enabled=(backend == "cupy"), min_features=256)
        try:
            with torch.no_grad():
                for idx in sorted(list(vis_batches.keys())):
                    vb = vis_batches.pop(idx)
                    s_obj = samples[idx]
                    n_slots = int((s_obj.input_ids == pad_id).sum().item())
                    vout = vis_tower(vb["pixel_values"].to(torch.bfloat16), grid_thw=vb["image_grid_thw"])
                    img_feats = vout.pooler_output if hasattr(vout, "pooler_output") else vout
                    if isinstance(img_feats, (tuple, list)):
                        img_feats = torch.cat([t.reshape(-1, hidden_size) for t in img_feats], dim=0)
                    else:
                        img_feats = img_feats.reshape(-1, hidden_size)
                    if n_slots <= 0 or img_feats.shape[0] < n_slots:
                        raise RuntimeError(
                            f"Vision feature slot mismatch on {s_obj.sample_id}: slots={n_slots}, feats={img_feats.shape}"
                        )
                    vis_feats[idx] = img_feats[:n_slots].to(torch.bfloat16).cpu().contiguous()
                    del vb, vout, img_feats
        finally:
            vis_patch.close()
            free_submodule_to_meta(vis_tower)
            del vis_tower, vis_batches
            free_cupy_pools()
            gc.collect()

    # Step 2: Stream token embeddings with ONLY embed_tokens.weight (~1.21 GiB) resident in RAM
    seq_lengths = [s.seq_len for s in samples]
    if min_post_write_free_gib > 0.0:
        from scripts.v2.common_io import assert_post_write_free_gib

        tot_tok = sum(seq_lengths)
        e0_need = (tot_tok * hidden_size * 2) if (e0_store_path is not None and not e0_store_path.is_file()) else 0
        h0_need = (tot_tok * hc_count * hidden_size * 2) if not h0_store_path.is_file() else 0
        if e0_store_path is not None and os.path.realpath(e0_store_path.parent) == os.path.realpath(h0_store_path.parent):
            assert_post_write_free_gib(
                h0_store_path.parent,
                e0_need + h0_need,
                min_free_gib=min_post_write_free_gib,
                label=f"init_e0_h0_{h0_store_path.name}",
            )
        else:
            if e0_store_path is not None:
                assert_post_write_free_gib(
                    e0_store_path,
                    tot_tok * hidden_size * 2,
                    min_free_gib=min_post_write_free_gib,
                    label=f"init_e0_{e0_store_path.name}",
                )
            assert_post_write_free_gib(
                h0_store_path,
                tot_tok * hc_count * hidden_size * 2,
                min_free_gib=min_post_write_free_gib,
                label=f"init_h0_{h0_store_path.name}",
            )

    e0_store: Optional[ResumableFlatSequenceStore] = (
        ResumableFlatSequenceStore(
            e0_store_path, seq_lengths, hc_count=1, hidden_size=hidden_size, create=True
        )
        if e0_store_path is not None
        else None
    )
    h0_store = ResumableFlatSequenceStore(
        h0_store_path, seq_lengths, hc_count=hc_count, hidden_size=hidden_size, create=True
    )

    emb_key = (
        "model.language_model.embed_tokens.weight"
        if "model.language_model.embed_tokens.weight" in st_index.weight_map
        else "model.embed_tokens.weight"
    )
    emb_w = st_index.load_tensors([emb_key], device="cpu", dtype=torch.bfloat16)[emb_key]
    with torch.no_grad():
        for s in samples:
            e_emb = F.embedding(s.input_ids, emb_w)  # [1, S, D] bf16
            if s.idx in vis_feats:
                vf = vis_feats.pop(s.idx)
                e_emb = e_emb.clone()
                e_emb[s.input_ids == pad_id] = vf
                del vf

            if e0_store is not None:
                e0_store.write_seq(s.idx, e_emb.view(1, s.seq_len, 1, hidden_size))
            h0 = e_emb.unsqueeze(2).expand(1, s.seq_len, hc_count, hidden_size).contiguous()
            h0_store.write_seq(s.idx, h0)
            del e_emb, h0

    del emb_w, vis_feats
    gc.collect()
    return samples, e0_store, h0_store


def AutoConfig_full(donor_dir: Path) -> Any:
    from transformers import AutoConfig

    cfg = AutoConfig.from_pretrained(str(donor_dir), trust_remote_code=False)
    if hasattr(cfg, "text_config"):
        cfg.text_config._attn_implementation = "sdpa"
    return cfg


def attach_non_moe_imatrix_hooks(
    layer: nn.Module,
    text_cfg: Any,
    bid: int,
    imat: LayerImatrixCollector,
) -> List[Any]:
    """Attach forward pre-hooks for all non-MoE quantizable GGUF weights in layer `bid`."""
    handles: List[Any] = []
    num_k_heads = int(getattr(text_cfg, "linear_num_key_heads", 0) or 0)
    num_v_heads = int(getattr(text_cfg, "linear_num_value_heads", 0) or 0)
    head_v_dim = int(getattr(text_cfg, "linear_value_head_dim", 128) or 128)

    handles.append(
        layer.attn_hyper_connection.input_mix_weight_down.register_forward_pre_hook(
            lambda _m, inp: imat.record_2d((f"blk.{bid}.hc_attn_down_inject.weight",), inp[0])
        )
    )
    handles.append(
        layer.attn_hyper_connection.input_mix_weight_up.register_forward_pre_hook(
            lambda _m, inp: imat.record_2d((f"blk.{bid}.hc_attn_up.weight",), inp[0])
        )
    )
    handles.append(
        layer.mlp_hyper_connection.input_mix_weight_down.register_forward_pre_hook(
            lambda _m, inp: imat.record_2d((f"blk.{bid}.hc_ffn_down_inject.weight",), inp[0])
        )
    )
    handles.append(
        layer.mlp_hyper_connection.input_mix_weight_up.register_forward_pre_hook(
            lambda _m, inp: imat.record_2d((f"blk.{bid}.hc_ffn_up.weight",), inp[0])
        )
    )

    if getattr(layer, "ple", None) is not None:
        handles.append(
            layer.ple.key_proj.register_forward_pre_hook(
                lambda _m, inp: imat.record_2d(
                    (f"blk.{bid}.ple_key.weight", f"blk.{bid}.ple_value.weight"), inp[0]
                )
            )
        )

    if layer.layer_type == "linear_attention":
        handles.append(
            layer.linear_attn.out_proj.register_forward_pre_hook(
                lambda _m, inp: imat.record_2d(
                    (f"blk.{bid}.ssm_out.weight",),
                    reorder_gdn_v_heads_activation(
                        inp[0].detach().reshape(-1, inp[0].shape[-1]),
                        num_k_heads=num_k_heads,
                        num_v_heads=num_v_heads,
                        head_v_dim=head_v_dim,
                    ),
                )
            )
        )
    else:
        handles.append(
            layer.self_attn.o_proj.register_forward_pre_hook(
                lambda _m, inp: imat.record_2d((f"blk.{bid}.attn_output.weight",), inp[0])
            )
        )

    return handles


class SingleLayerContext:
    """Materializes a single Qwen4ExpTextDecoderLayer (excluding MoE if desired, or full),
    wires SafeStreamingPLENGramEmbedding + QSAIndexerWrapper + optional CuPyLinearPatch,
    and cleanly frees everything on close()."""

    def __init__(
        self,
        bid: int,
        text_cfg: Any,
        st_index: SafetensorsIndex,
        rotary_emb: nn.Module,
        backend: str = "cpu",
        is_mtp: bool = False,
        preindex_ple_inputs: Optional[Sequence[torch.Tensor]] = None,
        skip_moe_experts: Optional[bool] = None,
    ) -> None:
        from transformers.models.qwen4_exp.modeling_qwen4_exp import Qwen4ExpTextDecoderLayer

        self.bid = int(bid)
        self.text_cfg = build_mtp_decoder_config(text_cfg) if is_mtp else text_cfg
        self.st_index = st_index
        self.rotary_emb = rotary_emb
        self.backend = backend
        self.is_mtp = bool(is_mtp)
        skip_exp = (self.backend == "cupy") if skip_moe_experts is None else bool(skip_moe_experts)

        with torch.device("meta"):
            self.layer = Qwen4ExpTextDecoderLayer(
                self.text_cfg, layer_idx=0 if is_mtp else self.bid
            )

        if is_mtp:
            prefix = "mtp.layers.0"
        elif any(k.startswith(f"model.language_model.layers.{self.bid}.") for k in st_index.weight_map):
            prefix = f"model.language_model.layers.{self.bid}"
        else:
            prefix = f"model.layers.{self.bid}"
        skip_pats = ("ngram_embedding.shard_", "mlp.experts.") if skip_exp else ("ngram_embedding.shard_",)
        materialize_submodule(
            self.layer,
            prefix,
            st_index,
            device="cpu",
            skip_patterns=skip_pats,
        )
        if getattr(self.layer, "mlp", None) is not None:
            self.layer.mlp._v2_st_source = (st_index, f"{prefix}.mlp")

        self.ple_streamer: Optional[SafeStreamingPLENGramEmbedding] = None
        if getattr(self.layer, "ple", None) is not None:
            self.ple_streamer = SafeStreamingPLENGramEmbedding(
                self.text_cfg,
                st_index,
                f"{prefix}.ple.ple_embedding",
            )
            if preindex_ple_inputs is not None:
                self.ple_streamer.preindex_for_sequences(preindex_ple_inputs)
            self.layer.ple.ple_embedding = self.ple_streamer

        if self.layer.layer_type != "linear_attention" and hasattr(self.layer.self_attn, "indexer"):
            self.layer.self_attn.indexer = QSAIndexerWrapper(self.layer.self_attn.indexer)

        self.gdn_wrapper: Optional[CuPyGatedDeltaNetWrapper] = None
        if backend == "cupy":
            if self.layer.layer_type == "linear_attention":
                self.linear_patch_attn = CuPyLinearPatch(self.layer.linear_attn.out_proj, enabled=True)
                self.gdn_wrapper = CuPyGatedDeltaNetWrapper(self.layer.linear_attn, self.text_cfg)
                self.layer.linear_attn = self.gdn_wrapper
            else:
                self.linear_patch_attn = CuPyLinearPatch(self.layer.self_attn, enabled=True)
                self.layer.self_attn = CuPyFastAttentionWrapper(self.layer.self_attn, self.text_cfg)
        else:
            self.linear_patch_attn = CuPyLinearPatch(
                self.layer.linear_attn if self.layer.layer_type == "linear_attention" else self.layer.self_attn,
                enabled=False,
            )
        self.linear_patch_hc1 = CuPyLinearPatch(self.layer.attn_hyper_connection, enabled=(backend == "cupy"))
        self.linear_patch_hc2 = CuPyLinearPatch(self.layer.mlp_hyper_connection, enabled=(backend == "cupy"))
        self.linear_patch_ple = (
            CuPyLinearPatch(self.layer.ple, enabled=(backend == "cupy"))
            if getattr(self.layer, "ple", None) is not None
            else None
        )

    @torch.no_grad()
    def forward_pre_moe(
        self,
        h_in_1_s_hc_d: torch.Tensor,
        sample: PreparedSample,
        imat: Optional[LayerImatrixCollector] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Run PLE (if layer 1) + attn_hc + attention + attn_combine + mlp_hc.

        Returns (h_mlp_in [1, S, D], hyper_input [1, S, hc*D], inj_ffn [1, S, hc]).
        """
        s_len = int(h_in_1_s_hc_d.shape[1])
        h_flat = h_in_1_s_hc_d.reshape(1, s_len, -1).to(torch.bfloat16)

        if getattr(self.layer, "ple", None) is not None:
            h_flat = h_flat + self.layer.ple(h_flat, sample.input_ids[:, :s_len], None, conv_mask=None)

        h_attn_in, hyper_input, inj_attn = self.layer.attn_hyper_connection(h_flat)
        if self.layer.layer_type == "linear_attention":
            if imat is not None:
                imat.record_2d(
                    (f"blk.{self.bid}.attn_qkv_gate.weight", f"blk.{self.bid}.ssm_beta_alpha.weight"),
                    h_attn_in,
                )
            h_attn_out = self.layer.linear_attn(h_attn_in, cache_params=None, attention_mask=None)
        else:
            if imat is not None:
                imat.record_2d(
                    (
                        f"blk.{self.bid}.attn_q.weight",
                        f"blk.{self.bid}.attn_k.weight",
                        f"blk.{self.bid}.attn_v.weight",
                        f"blk.{self.bid}.indexer.q_proj.weight",
                        f"blk.{self.bid}.indexer.k_proj.weight",
                    ),
                    h_attn_in,
                )
            cos, sin = compute_position_embeddings_for_sample(
                self.rotary_emb,
                {"mrope_position_ids": sample.mrope_position_ids},
                seq_len=s_len,
                device="cpu",
                dtype=torch.bfloat16,
            )
            q_pos = torch.arange(s_len)[None, None, :, None]
            k_pos = torch.arange(s_len)[None, None, None, :]
            if getattr(self.text_cfg, "_attn_implementation", "sdpa") == "sdpa":
                causal_mask = k_pos <= q_pos
            else:
                causal_mask = torch.where(
                    k_pos <= q_pos,
                    torch.zeros(1, dtype=torch.bfloat16),
                    torch.full((1,), torch.finfo(torch.bfloat16).min, dtype=torch.bfloat16),
                )
            h_attn_out, _ = self.layer.self_attn(
                h_attn_in, (cos, sin), attention_mask=causal_mask, past_key_values=None
            )

        inj1 = h_attn_out.unsqueeze(-2) * inj_attn.unsqueeze(-1)
        h_mid = hyper_input + inj1.flatten(-2)

        h_mlp_in, hyper_ffn, inj_ffn = self.layer.mlp_hyper_connection(h_mid)
        return h_mlp_in, hyper_ffn, inj_ffn

    @staticmethod
    @torch.no_grad()
    def combine_post_moe(
        mlp_out_1_s_d: torch.Tensor,
        hyper_ffn: torch.Tensor,
        inj_ffn: torch.Tensor,
        hc_count: int = 4,
        hidden_size: int = 2560,
    ) -> torch.Tensor:
        s_len = int(mlp_out_1_s_d.shape[1])
        inj2 = mlp_out_1_s_d.to(torch.bfloat16).unsqueeze(-2) * inj_ffn.unsqueeze(-1)
        h_out = hyper_ffn + inj2.flatten(-2)
        return h_out.reshape(1, s_len, hc_count, hidden_size)

    def close(self) -> None:
        if self.gdn_wrapper is not None:
            self.gdn_wrapper.close()
        self.linear_patch_attn.close()
        self.linear_patch_hc1.close()
        self.linear_patch_hc2.close()
        if self.linear_patch_ple is not None:
            self.linear_patch_ple.close()
        if self.ple_streamer is not None:
            self.ple_streamer.clear_preindex()
        free_submodule_to_meta(self.layer)
        free_cupy_pools()
        gc.collect()


def run_layer_resume_determinism_probe(
    mode: str,
    probe_bid: int,
    text_cfg: Any,
    st_index: SafetensorsIndex,
    rotary_emb: Any,
    backend: str,
    calib_samples: Sequence[PreparedSample],
    eval_samples: Sequence[PreparedSample],
    c_in_store: ResumableFlatSequenceStore,
    e_in_store: ResumableFlatSequenceStore,
    c_expected_out_store: Optional[ResumableFlatSequenceStore] = None,
    e_expected_out_store: Optional[ResumableFlatSequenceStore] = None,
    n_calib_probe: int = 2,
    n_eval_probe: int = 1,
) -> Dict[str, Any]:
    """OPUS §0.3a.4 Determinism Probe before resuming per-layer ping-pong execution.

    Modes:
    - 'prev_slot': Recomputes `probe_bid` (last completed layer) from `prev_slot` on up to
      `n_calib_probe` calib + `n_eval_probe` eval sequences and verifies rel-L2 <= 1e-3 against
      stored `cur_slot` outputs.
    - 'double_recompute': Used when `prev_slot` was overwritten mid-layer (e.g., Wave 2 bid=2
      bootstrap). Runs `probe_bid` forward twice from `cur_slot` on up to `n_calib_probe` calib
      + `n_eval_probe` eval sequences and verifies bit-equal / rel-L2 <= 1e-4 repeatability.
    """
    from scripts.v2.cupy_moe_backend import MoELayerWeights, forward_moe_v2

    if mode not in ("prev_slot", "double_recompute"):
        raise ValueError(f"Invalid determinism probe mode: {mode!r}")
    if mode == "prev_slot" and (c_expected_out_store is None or e_expected_out_store is None):
        raise ValueError("prev_slot determinism probe requires c_expected_out_store and e_expected_out_store")

    hc_count = int(text_cfg.hc_count)
    hidden_size = int(text_cfg.hidden_size)
    probe_c = list(calib_samples[: min(n_calib_probe, len(calib_samples))])
    probe_e = list(eval_samples[: min(n_eval_probe, len(eval_samples))])
    ple_in = [s.input_ids for s in probe_c] + [s.input_ids for s in probe_e]

    ctx = SingleLayerContext(
        bid=int(probe_bid),
        text_cfg=text_cfg,
        st_index=st_index,
        rotary_emb=rotary_emb,
        backend=backend,
        is_mtp=False,
        preindex_ple_inputs=ple_in,
    )
    moe_d = MoELayerWeights.from_hf_moe_block(ctx.layer.mlp, backend=backend)

    def _forward_sample(store: ResumableFlatSequenceStore, s: PreparedSample) -> np.ndarray:
        hm, hyp, inj = ctx.forward_pre_moe(store.read_seq(s.idx), s)
        yd = forward_moe_v2(moe_d, hm)
        out = ctx.combine_post_moe(yd, hyp, inj, hc_count, hidden_size)
        return out.to(torch.float32).numpy()

    rel_errors: List[float] = []
    try:
        if mode == "prev_slot":
            assert c_expected_out_store is not None and e_expected_out_store is not None
            for s in probe_c:
                y_rec = _forward_sample(c_in_store, s)
                y_exp = c_expected_out_store.read_seq(s.idx).to(torch.float32).numpy()
                rel_errors.append(
                    float(np.linalg.norm(y_rec - y_exp) / max(float(np.linalg.norm(y_exp)), 1e-12))
                )
            for s in probe_e:
                y_rec = _forward_sample(e_in_store, s)
                y_exp = e_expected_out_store.read_seq(s.idx).to(torch.float32).numpy()
                rel_errors.append(
                    float(np.linalg.norm(y_rec - y_exp) / max(float(np.linalg.norm(y_exp)), 1e-12))
                )
            limit = 1e-3
        else:
            for s in probe_c:
                y1 = _forward_sample(c_in_store, s)
                y2 = _forward_sample(c_in_store, s)
                rel_errors.append(
                    float(np.linalg.norm(y1 - y2) / max(float(np.linalg.norm(y1)), 1e-12))
                )
            for s in probe_e:
                y1 = _forward_sample(e_in_store, s)
                y2 = _forward_sample(e_in_store, s)
                rel_errors.append(
                    float(np.linalg.norm(y1 - y2) / max(float(np.linalg.norm(y1)), 1e-12))
                )
            limit = 1e-4
    finally:
        moe_d.close()
        ctx.close()
        free_cupy_pools()
        gc.collect()

    max_rel = max(rel_errors) if rel_errors else 0.0
    if max_rel > limit:
        raise RuntimeError(
            f"Resume determinism probe FAILED (mode={mode}, bid={probe_bid}): "
            f"max_rel_l2={max_rel:.3e} > limit={limit:.1e} (errors={rel_errors})"
        )
    return {
        "mode": mode,
        "probe_bid": int(probe_bid),
        "n_calib_probed": len(probe_c),
        "n_eval_probed": len(probe_e),
        "max_rel_l2": float(max_rel),
        "limit": float(limit),
        "passed": True,
    }
