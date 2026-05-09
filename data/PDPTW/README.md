# Li & Lim PDPTW 数据说明

本文档说明 `data/PDPTW/` 目录下 `Li & Lim benchmark` 数据的文件命名规则、实例文件格式，以及解文件格式。

## 1. 目录说明

当前目录下包含 6 组官方规模：

- `100/`
- `200/`
- `400/`
- `600/`
- `800/`
- `1000/`

每个子目录中通常包含两类文件：

- `*.txt`：实例定义文件
- `*.sol`：参考解 / 已知较优解文件

## 2. 文件名含义

### 2.1 总体结构

`Li & Lim` 的文件名前缀反映了实例的空间分布类型：

- `lc`：`clustered`，客户点聚类分布
- `lr`：`random`，客户点随机分布
- `lrc`：`random-clustered`，随机与聚类混合分布

后续数字反映实例类别与编号。不同规模下命名略有区别。

### 2.2 100 规模实例

例如：

- `lc101.txt`
- `lr201.txt`
- `lrc108.sol`

可按下面方式理解：

- `lc / lr / lrc`：空间分布类型
- 紧跟的 `1` 或 `2`：实例类别
  - 通常可理解为不同规划时域 / 时间窗风格
  - 一般 `1` 类更紧，`2` 类更松
- 最后两位：该类别下的实例编号

例如：

- `lc101`：聚类型、类别 1、第 01 个实例
- `lr201`：随机型、类别 2、第 01 个实例

### 2.3 200 及以上规模实例

例如：

- `lc1_2_1.txt`
- `lr2_4_7.txt`
- `lrc1_10_3.sol`

可按下面方式理解：

- `lc / lr / lrc`：空间分布类型
- 第一个数字 `1` 或 `2`：实例类别
- 第二个数字：规模组编号
  - `2` 对应 `200`
  - `4` 对应 `400`
  - `6` 对应 `600`
  - `8` 对应 `800`
  - `10` 对应 `1000`
- 最后一个数字：该组中的实例编号

例如：

- `lc1_2_1`：聚类型、类别 1、`200` 规模组、第 1 个实例
- `lrc1_10_3`：混合型、类别 1、`1000` 规模组、第 3 个实例

## 3. `.txt` 实例文件格式

### 3.1 第一行

实例文件第一行通常有 3 个数字，例如：

```text
50 200 1
```

含义通常为：

1. 车辆数上限
2. 车辆容量
3. 车辆速度

在 `Li & Lim` 数据中，旅行时间通常与欧氏距离一致，因此很多实现里主要使用前两项，速度常保持为 `1`。

### 3.2 后续各行

从第二行开始，每一行表示一个节点。第 0 行通常是仓库点，之后是提货点和送货点。

示例：

```text
0   70  70   0    0   1351  0   0   0
1   33  78  -20  750  809  90  71  0
71  30  79   20  561  632  90   0  1
```

各列含义如下：

| 列序号 | 字段名 | 含义 |
| --- | --- | --- |
| 1 | `id` | 节点编号 |
| 2 | `x` | X 坐标 |
| 3 | `y` | Y 坐标 |
| 4 | `demand` | 需求量 |
| 5 | `ready_time` | 最早开始服务时间 |
| 6 | `due_time` | 最晚开始服务时间 |
| 7 | `service_time` | 服务时长 |
| 8 | `pickup` | 对应提货点编号 |
| 9 | `delivery` | 对应送货点编号 |

### 3.3 关键字段解释

#### `id`

- 节点唯一编号
- `0` 一般表示仓库

#### `demand`

- 正数：提货点，装载增加
- 负数：送货点，装载减少
- `0`：通常是仓库点

例如：

- `demand = 20`：车辆在该点取走 20 单位货物
- `demand = -20`：车辆在该点交付 20 单位货物

#### `ready_time` 和 `due_time`

- 节点时间窗
- 常见做法是要求车辆在 `ready_time` 与 `due_time` 之间开始服务

#### `service_time`

- 在该节点完成装货 / 卸货所需的服务时间

#### `pickup` 和 `delivery`

这两列用于描述配对关系。

对同一请求的两个节点，通常有如下规则：

- 若当前行为提货点：
  - `pickup = 0`
  - `delivery = 对应送货点编号`
- 若当前行为送货点：
  - `pickup = 对应提货点编号`
  - `delivery = 0`
- 若当前行为仓库：
  - `pickup = 0`
  - `delivery = 0`

例如上面的样例中：

- 节点 `71` 是提货点，`delivery = 1`
- 节点 `1` 是与之配对的送货点，`pickup = 71`

因此一个请求由一对节点表示，并满足：

- 必须先访问提货点，再访问送货点
- 两点必须由同一辆车服务

## 4. `.sol` 解文件格式

`.sol` 文件记录实例的参考解或已知较优解。

例如：

```text
Instance name : lc1_2_1
Solution
Route  1 : 32 171 65 86 115 94 51 174 136 189
Route  2 : 177 3 88 8 186 127 98 157 137 183
```

主要内容包括：

- `Instance name`：实例名
- `Authors`、`Date`、`Reference`：解文件来源说明
- `Route k : ...`：第 `k` 条车辆路径

### 4.1 路径行含义

例如：

```text
Route  1 : 32 171 65 86 115 94 51 174 136 189
```

表示第 1 辆车按给定顺序访问这些节点。仓库点通常未显式写出，但默认路径从仓库出发并最终回到仓库。

### 4.2 如何与 `.txt` 配合使用

解析 `.sol` 时，一般做法是：

1. 从 `.txt` 中读取节点属性和配对关系
2. 从 `.sol` 中读取每条路径的访问顺序
3. 在程序中补上起点仓库 `0` 和终点仓库 `0`
4. 逐条验证：
   - 容量约束
   - 时间窗约束
   - 先提后送约束
   - 同车服务约束

## 5. 解析时的实用建议

建议在代码里把每个节点统一解析成如下字段：

- `id`
- `x`
- `y`
- `demand`
- `ready_time`
- `due_time`
- `service_time`
- `pickup`
- `delivery`

同时建议额外构造：

- `is_depot`
- `is_pickup`
- `is_delivery`
- `pair_id`

推荐判断逻辑：

- `id == 0`：仓库
- `delivery != 0`：提货点
- `pickup != 0`：送货点

## 6. 当前项目使用建议

建议先从 `data/PDPTW/100/` 中挑一个最小实例开始解析，例如：

- `lc101.txt`
- `lr101.txt`
- `lrc101.txt`

等读取、配对、时间窗和容量检查都跑通后，再切换到 `200` 及以上规模实例。

## 7. 当前项目中的统一读取方式

当前项目已经提供了统一读取模块 `pdptw`，可以把 `Li & Lim` 数据读成统一的数据结构。

主要入口：

- `pdptw.read_pdptw`
- `pdptw.PDPTWReadConfig`

### 7.1 支持的读取范围

支持下面三种常用方式：

1. 读取全部实例
2. 只读取某个规模目录，例如 `100`
3. 只读取某个具体 case，例如 `lc101` 或 `lc1_2_1`

### 7.2 配置字段

`PDPTWReadConfig` 包含这些字段：

- `dataset_dir`：数据目录，默认是 `data/PDPTW`
- `size`：指定规模，例如 `100`、`200`、`1000`
- `case_name`：指定实例名，例如 `lc101`、`lc1_2_1`
- `include_solution`：是否同时读取 `.sol` 文件，默认 `True`

### 7.3 示例

读取全部实例：

```python
from pdptw import read_pdptw

dataset = read_pdptw()
print(len(dataset.instances))
```

只读取 `100` 规模：

```python
from pdptw import PDPTWReadConfig, read_pdptw

dataset = read_pdptw(PDPTWReadConfig(size=100))
print(len(dataset.instances))
```

只读取 `100` 规模下的 `lc101`：

```python
from pdptw import PDPTWReadConfig, read_pdptw

dataset = read_pdptw(PDPTWReadConfig(size=100, case_name="lc101"))
instance = dataset.instances[0]
print(instance.name, instance.request_count)
```

跨目录按名称读取某个 case：

```python
from pdptw import PDPTWReadConfig, read_pdptw

dataset = read_pdptw(PDPTWReadConfig(case_name="lc1_2_1"))
instance = dataset.instances[0]
print(instance.size, instance.name)
```

### 7.4 统一数据结构

读取后会得到：

- `PDPTWDataset`
- `PDPTWInstance`
- `PDPTWNode`
- `PDPTWSolution`

其中：

- `PDPTWDataset.instances` 是实例列表
- `PDPTWInstance.nodes` 是节点列表
- `PDPTWInstance.nodes_by_id` 可按节点编号访问
- `PDPTWInstance.solution` 是 `.sol` 文件对应的路径解
- `PDPTWInstance.request_count` 是提货请求数
