# PostgreSQL 迁移指南

## 概述

本项目已从 SQLite 迁移到 PostgreSQL + Alembic。以下是完整操作步骤。

---

## 一、环境准备

### 1. 安装 PostgreSQL

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-client

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql -c "CREATE USER pipixia WITH PASSWORD 'pipixia_secret';"
sudo -u postgres psql -c "CREATE DATABASE pipixia OWNER pipixia;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pipixia TO pipixia;"
```

### 2. 或使用 Docker Compose（推荐）

```bash
# 启动 PostgreSQL 服务
docker compose up -d postgres

# 等待 PG 就绪
docker compose exec postgres pg_isready
```

### 3. 安装依赖

```bash
# 确保 alembic 已安装
pip3 install --break-system-packages alembic

# 确保 asyncpg 已安装（Docker 环境中已有）
pip3 install --break-system-packages asyncpg
```

---

## 二、配置

### 1. 更新 `.env` 文件

```bash
cp .env.example .env
# 编辑 .env，确保 DATABASE_URL 指向 PostgreSQL
```

`.env` 中关键配置：
```env
DATABASE_URL=postgresql+asyncpg://pipixia:pipixia_secret@localhost:5432/pipixia
```

### 2. 验证 Alembic 配置

```bash
# 查看迁移历史
alembic history

# 查看当前头节点
alembic heads

# 检查迁移状态
alembic check
```

预期输出：
```
<base> -> 0001 (head), empty message
0001 (head)
```

---

## 三、执行迁移

### 场景 A：全新部署（无旧数据）

```bash
# 1. 启动 PostgreSQL
docker compose up -d postgres

# 2. 运行 Alembic 迁移
make migrate

# 3. 创建管理员账号
make create-admin

# 4. 验证
make db-init
```

### 场景 B：从 SQLite 迁移数据

```bash
# 1. 确保 SQLite 备份存在
cp pipixia.db pipixia.db.backup

# 2. 启动 PostgreSQL
docker compose up -d postgres

# 3. 运行 Alembic 迁移（创建表结构）
make migrate

# 4. 执行数据迁移（SQLite → PostgreSQL）
make pg-migrate

# 5. 验证数据
make pg-shell
# 在 PG shell 中执行:
# SELECT count(*) FROM users;
# SELECT count(*) FROM shops;
# SELECT count(*) FROM products;
```

---

## 四、常用命令

```bash
# 查看所有命令及说明
make help

# 运行迁移到最新版本
make migrate

# 回退一次迁移
make migrate-down

# 进入 PostgreSQL shell
make pg-shell

# 创建管理员
make create-admin

# 查看数据库信息
python3 scripts/init_db.py info

# 创建管理员指定用户名密码
make create-admin USERNAME=myadmin PASSWORD=mypassword
```

---

## 五、新增迁移

当修改模型后，生成新的迁移文件：

```bash
# 1. 修改 api/models/ 中的模型

# 2. 生成迁移文件
alembic revision --autogenerate -m "描述性消息"

# 3. 审查生成的迁移文件
#    检查 migrations/versions/ 下的新文件

# 4. 应用迁移
alembic upgrade head
```

---

## 六、注意事项

### PostgreSQL 与 SQLite 的差异

| 特性 | SQLite | PostgreSQL |
|------|--------|------------|
| JSON 默认值 | `'{}'` | `'{}'::json` |
| Boolean 默认值 | `True` | `text('true')` |
| 自增列 | `AUTOINCREMENT` | `SERIAL` / `GENERATED ALWAYS AS IDENTITY` |
| 时间戳自动更新 | `onupdate=func.now()` | 需配合触发器或应用层处理 |

### 已做的兼容性处理

1. **Boolean 默认值**: 使用 `server_default=text('true')` 替代 `server_default=True`
2. **JSON 默认值**: 使用 `server_default=text("'{}'::json")` 替代 `server_default='{}'`
3. **Alembic env.py**: 支持异步引擎，区分 `history`/`heads` 等无数据库命令
4. **模型文件**: 所有表统一使用 `server_default=func.now()` 处理时间戳

### Docker 环境

`docker-compose.yml` 中 `api` 和 `worker` 服务已配置 PG 连接：
```yaml
environment:
  DATABASE_URL: postgresql+asyncpg://pipixia:pipixia_secret@postgres:5432/pipixia
```

容器内使用主机名 `postgres` 而非 `localhost` 连接 PG。

---

## 七、故障排查

### 问题 1: `ConnectionRefusedError: Connect call failed ('127.0.0.1', 5432)`

**原因**: PostgreSQL 服务未启动

**解决**:
```bash
# 检查 PG 状态
pg_isready

# 启动 PG
sudo systemctl start postgresql

# 或使用 Docker
docker compose up -d postgres
```

### 问题 2: `relation "users" does not exist`

**原因**: Alembic 迁移未执行

**解决**:
```bash
alembic upgrade head
```

### 问题 3: `duplicate key value violates unique constraint`

**原因**: 迁移重复执行或数据冲突

**解决**:
```bash
# 查看当前迁移版本
alembic current

# 如需重置（⚠️ 会清空数据）
alembic downgrade base
alembic upgrade head
```

### 问题 4: Alembic check 报错 `Can't use literal_binds setting without as_sql mode`

**原因**: env.py 配置问题

**解决**: 确保 `migrations/env.py` 中 `literal_binds=False`

---

## 八、数据迁移验证清单

迁移完成后，逐项验证：

- [ ] `alembic current` 显示 `0001 (head)`
- [ ] `docker compose exec postgres psql -U pipixia -d pipixia -c '\dt'` 显示 7 张表
- [ ] `users` 表有 5 条记录（来自 SQLite）
- [ ] `shops` 表有 4 条记录
- [ ] `products` 表有 4 条记录
- [ ] `listings`, `translates`, `risk_logs`, `profit_calibration` 表为空
- [ ] API 服务能正常读写数据
- [ ] Admin 账号能正常登录
