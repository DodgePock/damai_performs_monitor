# DAMAI_PERFORMS_MONITOR

监测大麦网演出新场次名称，关键词匹配成功即推送通知

### USAGE

#### 1. Clone

``` bash
git clone git@github.com:DodgePock/damai_performs_monitor.git
```

### 2. install requirements

``` bash
uv sync
```

about uv: [installation](https://docs.astral.sh/uv/getting-started/installation/)

### 3. edit settings.py

``` bash
cp settings_template.py settings.py
vim settings.py
```

### 4. run on schedule
use 'crontab' to run the monitor on a schedule

``` bash
crontab -e
```

for example, to run it every minutes, add following line to your crontab

``` bash
*/10 * * * * cd /path/to/damai_performs_monitor && uv run monitor.py
```
Replace `/path/to/damai_performs_monitor` with your actual project path.
