# A股分析 Skill

基于 [AKShare](https://github.com/akfamily/akshare) 的 A股实时分析工具，支持自然语言查询大盘、行情、资金流向等。

## 功能

- 📈 **实时大盘** - 上证、深证、创业板、沪深300、上证50 实时行情 + 成交额 + 市场情绪
- 🕯️ **K线查询** - 支持日/周/月线，显示开盘/收盘/涨跌幅
- 🚦 **涨跌停统计** - 涨停/跌停数量 + 前10涨停股
- 💰 **资金流向** - 主力净流入/流出，近5日趋势

## 环境要求

- Python 3.9+
- akshare: `pip install akshare`

## 安装

```bash
# 克隆仓库
git clone https://github.com/molezzz/openclaw-stock-skill.git
cd openclaw-stock-skill

# 安装依赖
pip install akshare pandas
```

## 使用

```bash
# 实时大盘
python main.py --query "A股大盘"

# K线查询
python main.py --query "茅台近30日K线"
python main.py --query "600519近10日K线"

# 涨跌停
python main.py --query "今日涨停"
python main.py --query "涨跌停统计"

# 资金流向
python main.py --query "茅台资金流向"
python main.py --query "600519资金流向"
```

## 支持的查询

| 类型 | 示例 |
|------|------|
| 大盘 | "A股大盘"、"上证指数"、"沪深300" |
| K线 | "茅台近30日K线"、"600519周线" |
| 涨跌停 | "今日涨停"、"跌停统计" |
| 资金流 | "茅台资金流向"、"北向资金" |

## 与 OpenClaw 集成

本项目可作为 OpenClaw 的 skill 使用：

1. 复制到 `skills/akshare-stock/`
2. 通过自然语言触发查询

## 数据来源

- [AKShare](https://github.com/akfamily/akshare) - 新浪财经/东方财富

**免责声明**：数据仅供参考，不构成投资建议。

## License

MIT
