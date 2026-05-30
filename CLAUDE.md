# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Forge** is a dual-purpose team performance measurement and gamification platform for the Yapsi software development team:

- **Forge Ops** — Analytics dashboards and metrics for PMs and tech leads to track team performance, velocity, and quality indicators
- **Forge Arena** — RPG-style gamification layer (classes, XP, achievements, leaderboard) for developers to create engagement and healthy competition

**Tech Stack:**
- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic
- Database: SQLite (MVP/v0.1-0.3) → PostgreSQL (v0.4+)
- Dependency Management: `uv` (fast Python package installer)
- API Integration: Jira Cloud REST API via httpx
- Frontend: Next.js (not yet implemented)

**Core Business Logic:**
- **CP (Complexity Points)**: Immutable per-subtask score calculated by the engine after approval
- **SP (Score Points)**: Variable gamification currency (sum of CP + bonuses/penalties)
- **Business Hours**: Work metrics exclude weekends, holidays, and lunch breaks (9am-6pm, 2pm-3pm lunch, CDMX timezone)
- **Engine Versions**: Algorithm rules versioned in YAML (`engine_versions.yaml`) for reproducible calculations

## Project Structure

```
forge/
├── backend/
│   ├── src/forge/
│   │   ├── core/              # Configuration, exceptions, logging, security, time_utils
│   │   ├── db/
│   │   │   ├── models/        # 18 SQLAlchemy models (Player, Epic, Story, Subtask, etc.)
│   │   │   ├── base.py        # DeclarativeBase
│   │   │   └── session.py     # Engine + SessionLocal
│   │   ├── etl/               # Jira integration (UC-01)
│   │   │   ├── jira_client.py
│   │   │   ├── time_metrics.py
│   │   │   ├── quality_metrics.py
│   │   │   ├── project_matcher.py
│   │   │   └── sync_orchestrator.py
│   │   ├── repositories/      # Data access layer (TODO: UC-02+)
│   │   ├── services/          # Business logic + engine (TODO: UC-02+)
│   │   ├── api/
│   │   │   └── routers/
│   │   │       └── integrations.py  # UC-01: /test-connection, /sync, /status
│   │   ├── schemas/           # Pydantic DTOs (TODO: UC-02+)
│   │   ├── scripts/
│   │   │   ├── cli.py         # Typer CLI (forge commands)
│   │   │   └── verify_setup.py
│   │   └── main.py            # FastAPI app
│   ├── alembic/
│   │   └── versions/
│   │       └── 001_initial_schema.py  # 18 tables
│   ├── seed/                  # YAML seed data
│   │   ├── engine_versions.yaml
│   │   ├── players_yapsi.yaml
│   │   └── README.md
│   ├── tests/
│   │   ├── conftest.py        # Fixtures (test_db_engine, test_session, sample_player)
│   │   ├── factories/         # factory-boy for test data
│   │   ├── fixtures/          # Mock Jira responses
│   │   ├── unit/              # Fast unit tests
│   │   └── integration/       # Slower tests with DB
│   ├── pyproject.toml
│   ├── .env.example
│   ├── Makefile
│   └── README.md
└── frontend/                  # Placeholder (Next.js)
```

## Commands Reference

All commands run from `backend/` directory. **Always use `uv` for dependency management** (not pip).

### Installation & Setup

```bash
# Install dependencies (first time or after pulling new deps)
uv sync

# Copy env template and configure
cp .env.example .env
# Edit .env: add Jira credentials + ENCRYPTION_KEY

# Generate encryption key for .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Initialize database (run migrations)
make db-init
# or: uv run alembic upgrade head

# Verify setup is correct
uv run python scripts/verify_setup.py
```

### Development Server

```bash
# Start FastAPI dev server (port 8000, hot reload)
make dev
# or: uv run uvicorn forge.main:app --reload --port 8000

# Check server is running
curl http://localhost:8000/
curl http://localhost:8000/health
```

### Database Operations

```bash
# Initialize DB (first time or after pulling new migrations)
make db-init

# Reset DB (DESTRUCTIVE: drops all tables + recreates)
make db-reset

# Create new migration after model changes
uv run alembic revision -m "description"

# View current migration version
uv run alembic current

# View migration history
uv run alembic history

# Rollback one migration
uv run alembic downgrade -1
```

### Data Operations (CLI)

```bash
# Test Jira connection
make test-jira
# or: uv run forge test-jira

# Sync data from Jira (UC-01)
make sync
# or: uv run forge sync

# Load seed data from YAML files
make seed
# or: uv run forge seed

# Recalculate engine metrics (force recalc all subtasks)
make recalc
# or: uv run forge recalc

# Open IPython shell with DB session loaded
make shell
# or: uv run forge shell

# Show project info
uv run forge info
```

### Testing

```bash
# Run all tests
make test
# or: uv run pytest

# Run only unit tests (fast)
make test-unit
# or: uv run pytest tests/unit -v

# Run with coverage (HTML + terminal report)
make test-cov
# or: uv run pytest --cov=forge --cov-report=html --cov-report=term

# Run specific test file
uv run pytest tests/unit/core/test_config.py -v

# Run specific test function
uv run pytest tests/unit/core/test_config.py::test_settings_load_from_env -v

# Run tests matching pattern
uv run pytest -k "test_business_hours" -v

# Exclude slow tests
uv run pytest -m "not slow"

# Exclude integration tests
uv run pytest -m "not integration"

# Verbose output with print statements
uv run pytest -v -s
```

### Code Quality

```bash
# Lint code (check only, no changes)
make lint
# or: uv run ruff check .

# Format code (auto-fix)
make format
# or: uv run ruff format .

# Type checking (strict mode)
make typecheck
# or: uv run mypy src/forge

# Run all quality checks
make lint && make typecheck
```

## Architecture Deep Dive

### Layer Overview

```
┌─────────────────────────────────────────┐
│         Jira Cloud REST API             │  External system
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│  etl/  (UC-01: Jira Integration)        │  Data ingestion layer
│  • JiraClient (httpx async)             │  • Fetches epics/stories/subtasks
│  • TimeMetrics (changelog → hours)      │  • Calculates work metrics
│  • QualityMetrics (QA/review data)      │  • Transforms Jira → domain
│  • ProjectMatcher (Jira key → Project)  │  • Handles API pagination
│  • SyncOrchestrator (coordinates all)   │  • Upserts to database
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│  db/models/  (18 SQLAlchemy models)     │  Persistence layer
│  • Player, Class, Avatar                │  • Domain entities
│  • Epic, Story, Subtask                 │  • Relationships
│  • Sprint, Project                      │  • Indexes
│  • Buff, Debuff                         │  • Constraints
│  • Achievement, AchievementUnlock       │  • Audit trail
│  • ShopItem, Redemption                 │  • Computed fields
│  • SpAdjustment, LeaderboardSnapshot    │
│  • EngineVersion, AuditLog              │
└────────────────┬────────────────────────┘
                 ↑
┌─────────────────────────────────────────┐
│  repositories/  (TODO: UC-02+)          │  Data access layer
│  • PlayerRepository                     │  • Query builders
│  • SubtaskRepository                    │  • Aggregations
│  • AchievementRepository                │  • Complex joins
│  • LeaderboardRepository                │  • Pagination
└────────────────┬────────────────────────┘
                 ↑
┌─────────────────────────────────────────┐
│  services/  (TODO: UC-02+)              │  Business logic layer
│  • EngineService (CP/SP calculation)    │  • Core algorithms
│  • PlayerService (XP, levels, class)    │  • Domain rules
│  • AchievementService (unlock logic)    │  • Validations
│  • LeaderboardService (ranking)         │  • Orchestration
│  • ForecastService (predictions)        │  • Transactions
└────────────────┬────────────────────────┘
                 ↑
┌─────────────────────────────────────────┐
│  api/routers/  (FastAPI endpoints)      │  Presentation layer
│  • integrations.py (UC-01: ✅)          │  • HTTP endpoints
│  • players.py (UC-02+: TODO)            │  • Request validation
│  • subtasks.py (UC-02+: TODO)           │  • Response formatting
│  • leaderboard.py (UC-02+: TODO)        │  • Auth/middleware
│  • achievements.py (UC-02+: TODO)       │  • Error handling
└─────────────────────────────────────────┘
```

### Key Domain Concepts

#### Complexity Points (CP) - Immutable Score
- **What**: Per-subtask score from 1-100 calculated by the engine
- **When**: Computed when subtask status = "Done" + approved by PM/TL
- **Immutability**: Once set, CP never changes (CPImmutableError if modified)
- **Factors**: Time to complete, QA attempts, review rejections, sprint context, buffs/debuffs
- **Use Case**: Objective work difficulty measurement for performance tracking

#### Score Points (SP) - Variable Gamification Currency
- **What**: Gamification points earned by players (sum of CP + bonuses/penalties)
- **When**: Recalculated on every sync or manual adjustment
- **Variability**: Can change due to team buffs, debuffs, achievements, manual adjustments
- **Factors**: CP base + team performance multipliers + individual bonuses
- **Use Case**: In-game currency for shop, leaderboard ranking, leveling up

#### Business Hours Calculation
- **Work Days**: Monday-Friday (excludes weekends + company holidays)
- **Work Hours**: 9:00 AM - 6:00 PM (9 hours total)
- **Lunch Break**: 2:00 PM - 3:00 PM (excluded from work time)
- **Net Work Hours**: 8 hours/day (9 - 1 hour lunch)
- **Timezone**: America/Mexico_City (CDMX)
- **Implementation**: `time_utils.py` converts Jira changelog timestamps → business hours

#### Engine Versions
- **Purpose**: Version algorithm rules for reproducible calculations
- **Storage**: YAML files in `seed/engine_versions.yaml`
- **Fields**: `version`, `name`, `description`, `active`, `rules_snapshot` (JSON)
- **Migration**: New engine versions don't recalculate old tasks (historical consistency)
- **Current**: v2.0 (default in settings)

### Database Schema (18 Tables)

#### Core Entities

**Player** (team members)
- Fields: `jira_account_id`, `display_name`, `email`, `class_id`, `avatar_id`, `level`, `xp`, `sp_balance`, `total_cp_earned`, `total_sp_earned`
- Relations: → Class, → Avatar, ← Subtask (assignee), ← AchievementUnlock, ← Redemption

**Class** (RPG roles)
- Fields: `name`, `description`, `icon`, `color_hex`, `buff_multiplier`, `buff_description`
- Example: Warrior (tank, +10% team defense), Mage (burst damage, +15% CP on complex tasks)

**Avatar** (player appearance)
- Fields: `name`, `image_url`, `rarity`, `unlock_condition`, `sp_cost`
- Rarities: common, rare, epic, legendary

**Project** (work contexts)
- Fields: `jira_project_key`, `name`, `description`, `color_hex`, `is_active`
- Relations: ← Epic, ← Story, ← Subtask

#### Work Hierarchy (Jira Mirror)

**Epic** (large initiatives)
- Fields: `jira_key`, `summary`, `description`, `status`, `project_id`, `total_cp`, `total_sp`, `progress_percent`, `story_count`, `completed_stories`
- Relations: → Project, ← Story

**Story** (user stories)
- Fields: `jira_key`, `summary`, `description`, `epic_id`, `story_points` (Jira native), `total_cp`, `total_sp`, `subtask_count`, `completed_subtasks`
- Relations: → Epic, ← Subtask

**Subtask** (atomic work units) — **30+ fields**
- **Identity**: `jira_key`, `summary`, `description`, `status`, `story_id`, `assignee_id`, `reporter_id`
- **Time Metrics**: `created_at`, `started_at`, `completed_at`, `work_time_minutes`, `elapsed_days`, `business_hours_spent`
- **Quality Metrics**: `qa_attempts`, `review_rejections`, `bugs_found`, `quality_score`
- **Engine Outputs**: `cp` (Complexity Points), `sp` (Score Points), `engine_version`
- **Context**: `sprint_id`, `labels`, `priority`
- Relations: → Story, → Player (assignee), → Sprint

**Sprint** (time boxes)
- Fields: `jira_sprint_id`, `name`, `goal`, `state`, `start_date`, `end_date`, `completed_cp`, `completed_sp`, `velocity`
- Relations: ← Subtask

#### Gamification

**Buff** (positive multipliers)
- Fields: `name`, `description`, `effect_type`, `multiplier`, `duration_days`, `sp_cost`, `icon`
- Types: team_cp_boost, individual_xp_bonus, shop_discount

**Debuff** (penalties)
- Fields: `name`, `description`, `effect_type`, `penalty`, `duration_days`, `trigger_condition`
- Types: missed_deadline, low_quality, blocked_too_long

**Achievement** (milestones)
- Fields: `key`, `title`, `description`, `category`, `tier`, `unlock_criteria`, `sp_reward`, `xp_reward`, `icon`
- Categories: velocity, quality, consistency, teamwork, streak
- Tiers: bronze, silver, gold, platinum

**AchievementUnlock** (player progress)
- Fields: `player_id`, `achievement_id`, `unlocked_at`, `progress_data`

**ShopItem** (purchasable rewards)
- Fields: `name`, `description`, `sp_cost`, `item_type`, `effect_data`, `stock`, `icon`
- Types: avatar, buff, cosmetic, power_up

**Redemption** (purchase history)
- Fields: `player_id`, `shop_item_id`, `sp_spent`, `redeemed_at`, `status`

#### Analytics & Audit

**SpAdjustment** (manual corrections)
- Fields: `player_id`, `amount`, `reason`, `adjusted_by`, `created_at`
- Use Case: Admin corrections, bonuses, penalties

**LeaderboardSnapshot** (time-series rankings)
- Fields: `snapshot_date`, `player_id`, `rank`, `sp`, `cp`, `level`, `achievements_count`
- Purpose: Historical leaderboard data for trend analysis

**EngineVersion** (algorithm versioning)
- Fields: `version`, `name`, `description`, `rules_snapshot`, `is_active`, `effective_from`

**AuditLog** (change tracking)
- Fields: `entity_type`, `entity_id`, `action`, `changes`, `user_id`, `extra_metadata`, `timestamp`
- Actions: CREATE, UPDATE, DELETE, SYNC, RECALC

### ETL Pipeline Deep Dive

**Flow: Jira Cloud → Transform → Database**

#### 1. JiraClient (`etl/jira_client.py`)
- **HTTP Client**: httpx AsyncClient with Basic Auth (email + API token)
- **Endpoints Used**:
  - `GET /rest/api/3/search` — JQL queries for epics/stories/subtasks
  - `GET /rest/api/3/issue/{key}` — Full issue details + changelog
  - `GET /rest/api/3/issue/{key}/changelog` — History of status changes
- **Features**:
  - Pagination (startAt/maxResults)
  - Retry logic (3 attempts with exponential backoff)
  - Rate limiting awareness
  - Error handling (JiraSyncError custom exception)

#### 2. TimeMetrics (`etl/time_metrics.py`)
- **Input**: Jira issue changelog (status transitions with timestamps)
- **Output**: `work_time_minutes`, `elapsed_days`, `business_hours_spent`
- **Algorithm**:
  1. Parse changelog for status changes ("In Progress" → "Done")
  2. Filter out weekend/holiday timestamps
  3. Subtract lunch hour (14:00-15:00) per day
  4. Convert to CDMX timezone
  5. Sum business hours between transitions
- **Edge Cases**: Handles tasks started before business hours, tasks spanning multiple days

#### 3. QualityMetrics (`etl/quality_metrics.py`)
- **Input**: Jira issue changelog + comments
- **Output**: `qa_attempts`, `review_rejections`, `bugs_found`, `quality_score`
- **Derivation Logic**:
  - QA attempts: Count transitions to/from "QA" status
  - Review rejections: Count "In Review" → "In Progress" transitions
  - Bugs found: Parse comments for bug keywords + linked bug issues
  - Quality score: 100 - (qa_attempts * 5) - (review_rejections * 10) - (bugs_found * 15)

#### 4. ProjectMatcher (`etl/project_matcher.py`)
- **Purpose**: Map Jira project keys → local `Project` model IDs
- **Cache**: In-memory dict of `{jira_key: project_id}`
- **Auto-Create**: If Jira project not in DB, creates new `Project` record

#### 5. SyncOrchestrator (`etl/sync_orchestrator.py`)
- **Orchestrates full sync**:
  1. Connect to Jira (validate credentials)
  2. Fetch epics (JQL: `type = Epic AND project IN (...)`)
  3. For each epic → fetch stories (JQL: `parent = {epic_key}`)
  4. For each story → fetch subtasks (JQL: `parent = {story_key}`)
  5. Calculate time/quality metrics per subtask
  6. Upsert to database (SQLAlchemy session)
  7. Log to AuditLog
- **Batching**: Processes in batches of 50 (configurable via `SYNC_BATCH_SIZE`)
- **Timeout**: 300 seconds max (configurable via `SYNC_TIMEOUT_SECONDS`)

### Configuration (`core/config.py`)

**Environment Variables (.env)**

```bash
# Application
APP_ENV=development  # development | staging | production
APP_NAME=Forge
APP_VERSION=0.1.0
DEBUG=true
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///./forge.db

# Jira Integration (REQUIRED)
JIRA_INSTANCE_URL=https://your-domain.atlassian.net
JIRA_USER_EMAIL=your-email@company.com
JIRA_API_TOKEN=YOUR_API_TOKEN_HERE  # Generate at https://id.atlassian.com/manage-profile/security/api-tokens

# Security (REQUIRED)
ENCRYPTION_KEY=YOUR_FERNET_KEY_HERE  # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# API Settings
API_V1_PREFIX=/api
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
MAX_UPLOAD_SIZE_MB=50

# Business Rules (CDMX timezone)
BUSINESS_HOURS_START=09:00
BUSINESS_HOURS_END=18:00
BUSINESS_HOURS_LUNCH_START=14:00
BUSINESS_HOURS_LUNCH_END=15:00
BUSINESS_HOURS_TIMEZONE=America/Mexico_City

# Engine Config
DEFAULT_ENGINE_VERSION=v2.0
ENABLE_AUTO_RECALC=true

# Jira Sync Settings
SYNC_BATCH_SIZE=50
SYNC_TIMEOUT_SECONDS=300
SYNC_RETRY_MAX=3

# Feature Flags (Arena features)
ENABLE_ARENA=true
ENABLE_ACHIEVEMENTS=true
ENABLE_SHOP=true
ENABLE_FORECAST=true
```

**Pydantic Settings Model**
- Type-safe access: `settings.jira_instance_url` (not dict lookup)
- Auto-parsing: strings → ints, bools, enums
- Validation: Required fields fail fast at startup
- Caching: `@lru_cache` decorator on `get_settings()` — only loads .env once
- CORS: `cors_origins` stored as string, parsed to list via `cors_origins_list` property

## Testing Conventions

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (DB, session, sample data)
├── factories/               # factory-boy builders
│   ├── player.py
│   ├── subtask.py
│   └── achievement.py
├── fixtures/                # Mock data
│   ├── jira_payloads/       # Mock Jira API responses (JSON)
│   └── seed_data/           # Test YAML files
├── unit/                    # Fast tests (no DB, no network)
│   ├── core/
│   │   ├── test_config.py
│   │   ├── test_time_utils.py
│   │   └── test_exceptions.py
│   ├── etl/
│   │   ├── test_time_metrics.py
│   │   └── test_quality_metrics.py
│   └── services/            # TODO
└── integration/             # Slower tests (DB + network mocking)
    ├── test_sync_flow.py
    ├── test_api_endpoints.py
    └── test_repositories.py  # TODO
```

### Key Fixtures (`conftest.py`)

```python
@pytest.fixture
def test_db_engine():
    """In-memory SQLite for fast tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def test_session(test_db_engine):
    """SQLAlchemy session for tests."""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def sample_player(test_session):
    """Pre-created Player for tests."""
    player = Player(
        jira_account_id="test-123",
        display_name="Test Player",
        email="test@example.com"
    )
    test_session.add(player)
    test_session.commit()
    return player
```

### factory-boy Example

```python
# tests/factories/player.py
import factory
from forge.db.models import Player

class PlayerFactory(factory.Factory):
    class Meta:
        model = Player

    jira_account_id = factory.Sequence(lambda n: f"jira-{n}")
    display_name = factory.Faker("name")
    email = factory.Faker("email")
    level = 1
    xp = 0
    sp_balance = 100
```

### Mocking Jira API (respx)

```python
import respx
from httpx import Response

@respx.mock
async def test_jira_fetch_epic(test_session):
    # Mock Jira API response
    respx.get("https://example.atlassian.net/rest/api/3/issue/PROJ-123").mock(
        return_value=Response(200, json={
            "key": "PROJ-123",
            "fields": {"summary": "Epic Title", "status": {"name": "Done"}}
        })
    )
    
    client = JiraClient(...)
    epic = await client.fetch_issue("PROJ-123")
    assert epic["key"] == "PROJ-123"
```

### Pytest Markers

```bash
# Skip slow tests
pytest -m "not slow"

# Only integration tests
pytest -m integration

# Only unit tests
pytest -m "not integration"
```

Mark tests in code:
```python
@pytest.mark.slow
def test_full_sync():
    ...

@pytest.mark.integration
def test_database_write():
    ...
```

### Coverage Best Practices

- **Target**: 80% overall coverage
- **Critical Paths**: 100% coverage for engine calculations, CP immutability, business hours logic
- **Skip**: Don't test framework code (FastAPI routes without business logic)
- **View Report**: `make test-cov` → open `htmlcov/index.html` in browser

## Code Style & Conventions

### Formatting Rules

- **Line Length**: 100 characters (ruff configured)
- **Imports**: Sorted via `ruff` (isort rules)
- **Docstrings**: Google style for public APIs
- **Type Hints**: Always use for function signatures, optional for local variables

### Ruff Configuration

```toml
[tool.ruff]
line-length = 100
select = ["E", "W", "F", "I", "B", "C4", "UP"]
ignore = ["E501"]  # Line too long (handled by formatter)
```

**Rules Applied:**
- E: PEP 8 errors
- W: PEP 8 warnings
- F: Pyflakes (unused imports, undefined names)
- I: isort (import sorting)
- B: bugbear (likely bugs)
- C4: comprehensions (simplify list/dict/set comprehensions)
- UP: pyupgrade (use modern Python syntax)

### Mypy Strict Mode

**All new code must pass `make typecheck`**

```toml
[tool.mypy]
strict = true
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Common Patterns:**
```python
# ✅ Good: Typed function signature
def calculate_cp(subtask: Subtask, engine_version: str) -> int:
    ...

# ✅ Good: Optional return type
def find_player(jira_id: str) -> Player | None:
    ...

# ❌ Bad: Missing return type
def calculate_cp(subtask):  # mypy error
    ...

# ❌ Bad: Untyped parameter
def find_player(jira_id) -> Player | None:  # mypy error
    ...
```

### Python 3.11+ Features

**Use modern syntax:**

```python
# ✅ Union types with |
def get_value() -> str | int:
    ...

# ✅ Match statements
match status:
    case "Done":
        return "completed"
    case "In Progress":
        return "active"
    case _:
        return "pending"

# ✅ Type hints for collections
players: list[Player] = []
scores: dict[str, int] = {}
```

### Import Organization

```python
# Standard library
import asyncio
from datetime import datetime, timedelta

# Third-party
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

# Local
from forge.core.config import get_settings
from forge.db.models import Player, Subtask
from forge.etl.jira_client import JiraClient
```

**Source Root**: `backend/src/` — always import as `from forge.xxx import ...`

## Common Workflows

### Adding a New Model

1. Create model in `src/forge/db/models/new_model.py`
2. Import in `src/forge/db/models/__init__.py`
3. Create migration: `uv run alembic revision -m "add new_model table"`
4. Edit generated migration in `alembic/versions/`
5. Apply migration: `make db-init`
6. Create factory in `tests/factories/new_model.py`
7. Write unit tests in `tests/unit/db/test_new_model.py`

### Adding a New API Endpoint

1. Create Pydantic schemas in `src/forge/schemas/new_feature.py`
2. Create router in `src/forge/api/routers/new_feature.py`
3. Register router in `src/forge/main.py`
4. Write integration test in `tests/integration/test_new_feature_api.py`
5. Update Makefile if needed
6. Document in this CLAUDE.md

### Running a Full Sync

```bash
# 1. Verify Jira connection
make test-jira

# 2. Run sync (can take 5-30 minutes depending on data size)
make sync

# 3. Verify data was loaded
uv run forge info

# 4. Check logs for errors
tail -f logs/forge.log  # if logging to file
```

### Debugging Failed Tests

```bash
# Run with verbose output
uv run pytest tests/unit/core/test_config.py -v -s

# Drop into debugger on failure
uv run pytest tests/unit/core/test_config.py --pdb

# Run only failed tests from last run
uv run pytest --lf

# Run only failed tests with verbose
uv run pytest --lf -v
```

### Troubleshooting

**Problem: `error parsing value for field "cors_origins"`**
- **Cause**: Pydantic Settings v2 incompatibility with list[str] field validators
- **Solution**: `cors_origins` changed to string type with property `cors_origins_list` (see config.py)

**Problem: `sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved`**
- **Cause**: SQLAlchemy reserves `metadata` attribute on models
- **Solution**: Renamed column to `extra_metadata` in AuditLog model

**Problem: `alembic.util.exc.CommandError: Can't locate revision identified by 'XXX'`**
- **Cause**: Database and migration history out of sync
- **Solution**: `make db-reset` (DESTRUCTIVE) or manually fix with `alembic stamp head`

**Problem: `forge: command not found`**
- **Cause**: CLI not installed or wrong Python environment
- **Solution**: Run `uv sync` to install CLI, use `uv run forge` instead of `forge`

**Problem: Jira API 401 Unauthorized**
- **Cause**: Invalid credentials or expired API token
- **Solution**: Regenerate token at https://id.atlassian.com/manage-profile/security/api-tokens

**Problem: Tests failing with "database is locked"**
- **Cause**: SQLite concurrency issue in tests
- **Solution**: Use in-memory DB (`:memory:`) for tests or separate test DB file per worker

## Roadmap & TODOs

### UC-01: Jira Integration ✅ (Complete)
- [x] JiraClient with Basic Auth
- [x] Time metrics from changelog
- [x] Quality metrics derivation
- [x] Project matching
- [x] Sync orchestrator
- [x] CLI commands (sync, test-jira)
- [x] API endpoints (/test-connection, /sync, /status)

### UC-02: Player Management (In Progress)
- [ ] PlayerRepository (CRUD + queries)
- [ ] PlayerService (business logic)
- [ ] API endpoints (GET /players, GET /players/{id}, PATCH /players/{id})
- [ ] Schemas (PlayerResponse, PlayerUpdate)
- [ ] Tests (unit + integration)

### UC-03: Subtask Metrics (In Progress)
- [ ] SubtaskRepository (filtering, aggregations)
- [ ] EngineService (CP/SP calculation algorithm)
- [ ] API endpoints (GET /subtasks, GET /subtasks/{id})
- [ ] Schemas (SubtaskResponse, SubtaskFilters)
- [ ] Tests (engine calculation edge cases)

### UC-04: Leaderboard (Planned)
- [ ] LeaderboardRepository (ranking queries)
- [ ] LeaderboardService (snapshot generation)
- [ ] API endpoints (GET /leaderboard, GET /leaderboard/history)
- [ ] Real-time updates (WebSocket or SSE)
- [ ] Tests (ranking algorithm, ties)

### UC-05+: Achievements, Shop, Forecasting (Planned)
- [ ] Achievement unlock logic
- [ ] Shop item purchase flow
- [ ] Forecast predictions (ML or heuristics)
- [ ] Admin dashboard endpoints
- [ ] Frontend (Next.js)

## Resources

- **Jira Cloud REST API**: https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/en/20/
- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- **uv Documentation**: https://github.com/astral-sh/uv
- **Alembic Tutorial**: https://alembic.sqlalchemy.org/en/latest/tutorial.html

---

**Last Updated**: 2026-05-20  
**Current Version**: v0.1.0 (MVP)  
**Maintainer**: Forge Team @ Yapsi

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Working model:** This project is driven by a "master chat" (an architect Claude instance on claude.ai)
> that designs work packages and reviews Claude Code's output. Claude Code executes one work package
> (WP) per session and ends every session with a **Handoff Report** (format in `FORGE_MASTER_PLAN.md`).
> When in doubt about scope or sequencing, follow the active WP spec, not improvisation.

---

## Project Overview

**Forge** is a dual-purpose team performance + gamification platform for the Yapsi dev team:

- **Forge Ops** — dashboards and metrics for PM / tech leads (velocity, quality, forecast, cost)
- **Forge Arena** — RPG gamification for devs (classes, avatars, XP, achievements, leaderboard, shop)

**Stack:**
- Backend: Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, `uv`
- DB: SQLite (MVP) → PostgreSQL (v0.4+)
- Frontend: Next.js 16 (App Router), TypeScript, Tailwind v4, shadcn/ui
- Integration: Jira Cloud REST v3 via httpx async
- Jira instance: `https://beyapsi-org.atlassian.net` (project key `YAP`)
- Repo: monorepo (`forge/` with `backend/` + `frontend/`), git on `master`

**Core domain logic:**
- **CP (Complexity Points)** — per-subtask, immutable after PM approval (`CPImmutableError` if mutated)
- **SP (Score Points)** — gamification currency: `CP × multipliers + bonuses − penalties`
- **Business hours** — exclude weekends, holidays, lunch (9-18h, 14-15h lunch, America/Mexico_City)
- **Engine versions** — versioned rules for reproducible calculations

---

## CURRENT STATE (29 May 2026) — read this first

### Real data synced from Jira
| Entity | Count |
|---|---|
| Players | 14 |
| Projects | 1 (YAP) |
| Epics | 44 |
| Stories | 142 |
| Subtasks | 383 (237 Done) |
| Subtasks w/ approved CP | 8 / 383 (approval flow UC-04 not built) |
| Sprints | 46 (32 closed, W22 active, 12 future) |

### What's BUILT and working
- ✅ **UC-01 Jira ETL** — full sync pipeline (jira_client, time_metrics, quality_metrics, project_matcher, sync_orchestrator)
- ✅ **Dashboard Service + API** — `GET /api/dashboard/sprint?project_code=&sprint_id=` with KPIs, area progress, player status, alerts
- ✅ **Engine CP/SP v2.0** — cp_calculator, multiplier_calculator, sp_calculator, debuff_detector, engine_orchestrator (no approval UI yet)
- ✅ **Repositories layer** — player, sprint, subtask, project, sp_adjustment + generic base
- ✅ **Sprint management** — `make sprint-generate` (idempotent weekly sprint generation, Mon-Sun)
- ✅ **Frontend dashboard** — `/dashboard` Server Component consuming the dashboard API; OpsHeader (project filter, sync), sidebar nav, 6 components rendering live data

### What's NOT built (the work ahead)
Ops admin APIs (UC-02/04/05/06/07), Arena entirely (UC-09–15), Pulse (UC-16), Monthly MVP (UC-17), and the frontend for all of the above. Overall completion ≈ 35%.

---

## PROJECT DIRECTION — Ritmo Operativo migration (ACTIVE)

The biggest near-term change: **the Sprint model is being replaced by the Ritmo Operativo model** (JPDS Doc 03.1). This is decided and canonical. Do not build new features on the legacy `sprints` table once WP-01 lands.

### Three temporal horizons (replace the Sprint)
| Horizon | Window | Purpose | Commits scope? |
|---|---|---|---|
| **Pulso** | Live / real-time | Absorb chaos without polluting metrics | No |
| **Ciclo** | Mon–Fri (1 work week) | Ritual unit: MVP, penalties, weekly leaderboard | No |
| **Ventana Móvil** | 4 rolling closed cycles | Forecast (P30/P50/P85), cost per area, dir comms | Probabilistic only |

### Cycle lifecycle
`planned → active → closed → archived`
- `planned → active`: Monday 00:00 (auto, scheduler)
- `active → closed`: Friday 18:00 + ritual (MVP assigned + penalties applied) — manual
- `closed → archived`: 7 days after close (auto, scheduler)
- Only ONE `active` cycle at a time (unique index)
- Closed cycle is immutable except MVP edit within 24 business hours

### What changes vs the old Sprint
- Table `sprints` → `cycles` (adds iso_year, iso_week, 4 states, closing_snapshot_json)
- FK rename in 3 tables: `sprint_id` → `cycle_id` (subtasks, sp_adjustments, leaderboard_snapshots)
- New tables: `mvp_monthly`, `forecast_snapshots`
- New SQL views: `cycles_active`, `cycle_metrics`, `rolling_window_4`, `rolling_window_4_by_area`, `pulse_now`, `current_forecast_by_epic`
- `leaderboard_snapshots.period_type` adds `'weekly'`, `'rolling_4'`
- MVP semanal: **+5 SP** (buff B17, was +10) | MVP del mes: **+10 SP** (new buff B17M)
- Engine bump v2.0 → v2.1

Reference specs (keep in `backend/specs/` or `docs/`): `Documento_03.1_Ritmo_Operativo.md`, `forge_entidades_v2_ciclos.md`, `UC-16_pulso_operativo.md`, `UC-17_cierre_mensual.md`.

---

## Commands Reference

All commands from `backend/`. Always use `uv` (never pip).

```bash
# Setup
uv sync                              # install deps
cp .env.example .env                 # then fill Jira creds + ENCRYPTION_KEY
make db-init                         # alembic upgrade head
uv run python scripts/verify_setup.py

# Dev
make dev                             # uvicorn :8000 hot reload
curl http://localhost:8000/health

# DB
make db-init                         # apply migrations
make db-reset                        # DESTRUCTIVE drop+recreate
uv run alembic revision -m "msg"     # new migration
uv run alembic current               # current version
uv run alembic downgrade -1          # rollback one

# Data ops (CLI)
make sync                            # pull from Jira (UC-01)
make seed                            # load YAML catalogs
make recalc                          # rerun engine on all subtasks
make sprint-generate                 # generate weekly sprints forward (idempotent)
make shell                           # ipython with DB context

# Tests
make test                            # all
make test-unit                       # fast only
make test-cov                        # coverage HTML+term
uv run pytest tests/unit/core/test_config.py::test_x -v   # single

# Quality
make lint                            # ruff check
make format                          # ruff format
make typecheck                       # mypy strict
```

---

## Architecture (layers)

```
Jira Cloud REST API
   ↓
etl/            JiraClient, TimeMetrics, QualityMetrics, ProjectMatcher, SyncOrchestrator
   ↓
db/models/      SQLAlchemy models (Player, Epic, Story, Subtask, Cycle*, Buff, Debuff,
                Achievement, ShopItem, SpAdjustment, LeaderboardSnapshot, EngineVersion, AuditLog ...)
   ↑
repositories/   data access (player, subtask, cycle*, project, sp_adjustment + base)
   ↑
services/       business logic + engine (dashboard_service, engine/*, + UC services as built)
   ↑
scheduler/      APScheduler jobs (cycle open/close-notify/archive) — added in cycles refactor
   ↑
api/routers/    FastAPI endpoints (integrations ✅, dashboard ✅, + per-UC)
   ↑
schemas/        Pydantic DTOs
```

(* `Cycle` replaces `Sprint` after WP-01.)

### Key engine concepts
- **CP** computed from talla (XS=1,S=2,M=3,L=5,XL=8; XXL=13 → must be split). L/XL require PM approval (UC-04). Immutable once `cp_approved_at` set.
- **SP** = `CP × M_calidad × M_eficiencia × M_dificultad × M_lider × M_cooperacion + flat_bonuses − penalties`. All multipliers default 1.0.
- **Business hours** in `core/time_utils.py` — single source of truth for time math.

---

## Code Style & Conventions

- Line length 100 (ruff). Rules: E,W,F,I,B,C4,UP.
- mypy strict; all new code must pass `make typecheck` (typed signatures, `X | None`, etc.).
- Python 3.11+: `match`, `X | Y` unions, `list[T]`/`dict[K,V]`.
- Source root `backend/src/` — imports as `from forge.xxx import ...`.
- Docstrings Google style for public APIs.

### Adding a model
1. `src/forge/db/models/x.py` → 2. export in `__init__.py` → 3. `alembic revision` → 4. edit migration → 5. `make db-init` → 6. factory in `tests/factories/` → 7. unit test.

### Adding an endpoint
1. schema in `src/forge/schemas/` → 2. router in `src/forge/api/routers/` → 3. register in `main.py` → 4. integration test → 5. document here.

---

## Testing Conventions

- `tests/conftest.py`: `test_db_engine` (in-memory SQLite), `test_session`, `sample_player`.
- `tests/factories/` (factory-boy), `tests/fixtures/jira_payloads/` (respx mocks).
- Markers: `slow`, `integration`, `e2e` — exclude with `-m "not integration"`.
- Async mode auto. Coverage target 80% overall; 100% on engine, CP immutability, business hours.

---

## Troubleshooting (known issues)

| Problem | Fix |
|---|---|
| `error parsing value for field "cors_origins"` | `cors_origins` is a string + `cors_origins_list` property (config.py) |
| `Attribute name 'metadata' is reserved` | AuditLog column renamed to `extra_metadata` |
| `Can't locate revision 'XXX'` | `make db-reset` or `alembic stamp head` |
| `forge: command not found` | `uv sync`, then `uv run forge` |
| Jira 401 | regenerate API token |
| `database is locked` in tests | use `:memory:` DB |

---

## Roadmap (work-package based)

Sequenced by dependency. Each WP = one Claude Code session with a Handoff Report. Detail in `FORGE_MASTER_PLAN.md`.

- [ ] **WP-01** — DB refactor: Sprints → Cycles (Ritmo Operativo schema + backend + dashboard) ← **ACTIVE**
- [ ] **WP-02** — UC-04 CP approval flow (backend + Ops UI)
- [ ] **WP-03** — UC-05 Cycle close + MVP semanal (+5 SP, snapshots, forecast trigger)
- [ ] **WP-04** — UC-06 Manual penalties + appeals
- [ ] **WP-05** — UC-07 Forecast P30/P50/P85 + UC-16 Pulse
- [ ] **WP-06** — UC-17 Monthly MVP close (+10 SP)
- [ ] **WP-07** — UC-02 Players admin
- [ ] **WP-08** — UC-09 Arena auth (login/sessions)
- [ ] **WP-09** — UC-15 + UC-10 Onboarding (class/avatar) + Profile
- [ ] **WP-10** — UC-11 + UC-12 Leaderboard + SP detail
- [ ] **WP-11** — UC-13 + UC-14 Achievements + Shop
- [ ] **WP-12** — Frontend polish + E2E across Ops & Arena

### Done
- [x] **UC-01** Jira integration (ETL, API, CLI)
- [x] Dashboard service + API + frontend dashboard
- [x] Engine CP/SP v2.0
- [x] Repositories layer
- [x] Sprint management CLI

---

**Last Updated:** 2026-05-29 · **Version:** v0.1.x (MVP) · **Maintainer:** Forge Team @ Yapsi