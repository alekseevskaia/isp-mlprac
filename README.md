# mlcourse-prac

Проверяющая система для прака по спецкурсу ML.

## Как это все использовать

Требования к серверу:

- Tesla A100 80 GB (GPU с индексом 0 всегда должен быть свободен)
- Docker с включенным NVIDIA runtime
- Poetry (https://python-poetry.org/)

### 1. Подготовка файлов на сервере

- Скопировать директорию с проектом в `/opt/mlcourse-prac` на сервере
- Создать директорию `/opt/mlcourse-prac/solutions` для хранения БД и решений студентов
- Создать директорию `/opt/mlcourse-prac/data`, в которой разместить наборы картинок и обученную
модель с бэкдором (см. конфиг `mlcourse.conf`)

### 2. Вставить недостающие значения в конфиг `mlcourse.conf`

### 3. Собрать wheel проверяющей системы для установки в контейнер, собрать сам контейнер:

```
poetry build
docker build -t mlcourse .  # не менять название образа
```

### 4. Скопировать systemd unit и включить сервис:

```
cp mlcourse.service /lib/systemd/system/
systemctl enable mlcourse
systemctl start mlcourse
```
