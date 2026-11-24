# SmartLLM Studio `v0.0.7-beta`

[English](README.md) | **Русский**

Локальный офлайн-конструктор многостраничных сайтов на вашей видеокарте NVIDIA (12 ГБ видеопамяти, 32 ГБ ОЗУ). Studio работает только на `127.0.0.1:8090`.

> **Публичная бета для тестирования.** Сгенерированные картинки иногда получаются с ошибками (анатомия, несовпадение с брифом). Об ошибках и с отзывами пишите в [GitHub Issues](https://github.com/VKVstudio/SmartLLM/issues).

Полная документация (живые демо, как это работает, требования, известные ограничения, планы) — в [основном README](https://github.com/VKVstudio/SmartLLM/blob/main/README.ru.md).

## Запуск

**Windows 11:** `powershell -ExecutionPolicy Bypass -File .\install.ps1`, затем `.\smartllm-studio.bat`

**Linux:** `./install.sh`, затем `./bin/smartllm-studio`

Откройте http://127.0.0.1:8090. Установщики создают окружение Python с Pillow и не скачивают веса моделей. Если моделей или движков нет, Studio предложит скачать всё в один клик (запустится [`setup_bundle.py`](https://github.com/VKVstudio/SmartLLM/blob/main/scripts/release/setup_bundle.py)), либо можно указать пути в **Настройках**.

## Лицензия

[FSL-1.1-ALv2](LICENSE.md), через 2 года переходит в Apache-2.0. Результаты принадлежат вам: [OUTPUTS.md](OUTPUTS.md). См. также [TRADEMARKS.md](TRADEMARKS.md) и [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
