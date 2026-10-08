# Dataset: GA4 export of the Google Merchandise Store (obfuscated sample)

All facts below were verified against the data. Follow them unless a query result shows otherwise.

## Table

- `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*` — one row per event, one table per day (`events_YYYYMMDD`).
- Date range: **2020-11-01 to 2021-01-31** (92 days). Nothing exists outside it.
  - "November" = Nov 2020, "December" = Dec 2020, "January" = Jan 2021.
  - Relative dates ("last month", "last week") are relative to 2021-01-31, the last day of data. Say which dates you used.
- **Always filter dates with `_TABLE_SUFFIX`** (e.g. `_TABLE_SUFFIX BETWEEN '20201201' AND '20201231'`), not `event_date`: it skips whole tables and scans less data. Monthly bucket: `SUBSTR(_TABLE_SUFFIX, 1, 6)`.
- Scale: ~4.3M events, ~270K users, ~360K sessions, ~5.7K purchase events. One web stream only.

## Columns you will need

| Column | Type | Notes |
|---|---|---|
| `event_name` | STRING | See event list below |
| `event_date` | STRING `YYYYMMDD` | Prefer `_TABLE_SUFFIX` for filtering |
| `event_timestamp` | INT64 (microseconds) | `TIMESTAMP_MICROS(event_timestamp)` |
| `user_pseudo_id` | STRING | The user identifier (`user_id` is always NULL) |
| `event_params` | ARRAY<STRUCT<key, value STRUCT<string_value, int_value, double_value, float_value>>> | See pattern below |
| `ecommerce.purchase_revenue_in_usd` | FLOAT64 | Order revenue, on `purchase` events. Never NULL there |
| `ecommerce.transaction_id` | STRING | See data-quality notes |
| `items` | ARRAY<STRUCT<item_id, item_name, item_brand, item_category, price_in_usd, quantity, item_revenue_in_usd, ...>> | Products on the event |
| `device.category` | STRING | `desktop`, `mobile`, `tablet` |
| `device.operating_system`, `device.web_info.browser` | STRING | |
| `geo.country`, `geo.region`, `geo.city` | STRING | |
| `traffic_source.source`, `.medium`, `.name` | STRING | **User's first-touch acquisition**, see below |

Use `*_in_usd` fields only: `ecommerce.purchase_revenue` (no suffix) is NULL on some purchases.

## Events

Funnel order: `session_start` → `page_view` → `view_item` → `add_to_cart` → `begin_checkout` → `add_shipping_info` → `add_payment_info` → `purchase`.
Others: `first_visit` (new users), `user_engagement`, `scroll`, `view_promotion`, `select_promotion`, `select_item`, `view_search_results`, `view_item_list`, `click`.

## Patterns

Read an event parameter:

```sql
(SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_title') AS page_title
(SELECT value.int_value    FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS ga_session_id
```

Sessions: a session is (`user_pseudo_id`, `ga_session_id`); count with
`COUNT(DISTINCT CONCAT(user_pseudo_id, CAST(ga_session_id AS STRING)))`. `ga_session_id` is present on every event.

Useful param keys: `ga_session_id`, `ga_session_number`, `page_location`, `page_title`, `page_referrer`, `engagement_time_msec`, `session_engaged`, `source`/`medium`/`campaign` (see below), `search_term`, `payment_type`, `coupon`, `promotion_name`.

## Revenue — two levels, never mix them

- **Order level:** `SUM(ecommerce.purchase_revenue_in_usd)` over rows with `event_name = 'purchase'`. Use for totals, trends, devices, channels, countries.
- **Product level:** `SUM(i.item_revenue_in_usd)` from `FROM ..., UNNEST(items) AS i WHERE event_name = 'purchase'`. Use for anything per product, category or brand. Units sold: `SUM(i.quantity)`.
- **Never sum `purchase_revenue_in_usd` after `UNNEST(items)`** — the order total is repeated once per item and gets multiplied.
- Totals: order-level ≈ $362.2K; product-level ≈ $362.1K. Revenue values are whole dollars (obfuscation).
- "Purchases" is ambiguous: purchase events (orders), or units (`SUM(quantity)`) for products. Say which you used.

## Traffic source — important caveat

- `traffic_source.source / medium / name` is the source that **first acquired the user**, not the source of the session that converted. When answering channel questions with it, say so ("first-touch source").
- Session-level `source` / `medium` / `campaign` exist in `event_params`, but only on ~1/3 of events and not on `session_start`. Use them only if the user explicitly asks for session-level attribution, and state the coverage limitation.

## Data-quality notes (mention when they affect an answer)

- **Obfuscation placeholders:** `<Other>`, `(data deleted)` and `(not set)` appear in traffic sources, item names and other dimensions. They are real rows; keep them in totals but call them out, and exclude them when ranking named things (e.g. top products).
- **Item arrays on non-purchase events are noisy:** `view_item` events carry up to 12 items (average ~7) and `add_to_cart` up to 12 (average ~11), not just the product being viewed. Per-product view or cart counts are therefore inflated, and view-to-purchase rates per product are only useful for relative comparison. Say this when you compute them.
- **Join products by `item_name`, not `item_id`** — item IDs are obfuscated differently across event types and almost never match.
- **Transaction IDs:** ~900 purchase events have `transaction_id` NULL or `(not set)`, and ~300 IDs appear more than once. Revenue figures in this app sum all purchase events (no de-duplication); mention this if the user asks about order counts or exact revenue.
