# Golden question results

| Case | Result | Key numbers | Ungrounded numbers | Queries | Time |
|---|---|---|---|---|---|
| total_users | pass | users: answer | none | 1 | 22s |
| top_products_revenue | pass | #1 Google Zip Hoodie F/C revenue: answer | none | 1 | 20s |
| revenue_over_time | pass | Nov 2020 revenue: answer<br>Dec 2020 revenue: answer<br>Jan 2021 revenue: answer | 362,165 | 2 | 40s |
| nov_vs_dec | pass | Nov revenue: answer<br>Dec revenue: answer | none | 2 | 36s |
| revenue_by_source | pass | google / organic revenue: answer | 131,163, 36.2 | 2 | 38s |
| revenue_by_device | pass | desktop revenue: answer<br>mobile revenue: answer | none | 1 | 23s |
| most_purchased_products | pass | #1 Google Clear Pen 4-Pack units: answer | none | 2 | 41s |
| views_vs_purchases | manual | — | 5,000 | 4 | 72s |
| followup_chain | pass | Crewneck Sweatshirt Navy, Dec: answer<br>Crewneck Sweatshirt Navy, Nov: answer | none | 5 | 87s |
| ambiguous | manual | — | none | 0 | 3s |

## total_users

> How many users visited the store?

A total of **270,154 unique users** visited the Google Merchandise Store across **360,129 sessions**.

- **December 2020** had the highest activity with 104,315 active users.
- **January 2021** followed with 94,790 active users.
- **November 2020** recorded 79,421 active users.

Note: Data covers the entire available dataset period from November 1, 2020 to January 31, 2021. Users are identified by their GA4 pseudo-ID (`user_pseudo_id`).

## top_products_revenue

> What were the top 10 products by revenue?

The top product by revenue was the **Google Zip Hoodie F/C**, generating **$13,788** from 273 units sold.

- **Google Crewneck Sweatshirt Navy** followed in second place with **$10,714** in revenue across 236 units.
- Apparel dominated the entire top 10 list, with hoodies, sweatshirts, jackets, and fleece apparel making up the highest-earning items.
- **Super G Unisex Joggers** had the highest sales volume among the top 10 products with 308 units sold ($9,529 in revenue).

Note: Data covers November 1, 2020 through January 31, 2021, and excludes obfuscation placeholder values such as `<Other>`.

## revenue_over_time

> How did revenue change over time?

Total revenue across the three-month dataset was **$362,165**, peaking in December 2020 before dropping sharply in January 2021.

- November 2020 generated $144,260 across 2,054 purchase events, rising steadily throughout the month.
- December 2020 reached the highest monthly total at **$160,555** (an 11.3% month-over-month increase) across 2,434 purchase events.
- January 2021 dropped to **$57,350** (a 64.3% month-over-month decline) across 1,204 purchase events.
- On a weekly basis, revenue peaked at $59,865 during the week of December 7, 2020, before tapering off late in the month.

Note: Data covers November 1, 2020 through January 31, 2021, and revenue reflects order-level totals without transaction deduplication.

## nov_vs_dec

> Compare revenue between November and December.

Revenue increased by **11.3%** from **$144,260** in November 2020 to **$160,555** in December 2020.

- Total monthly revenue rose by $16,295.
- Order volume grew by 18.5%, increasing from 2,054 purchase events in November to 2,434 in December.
- Average order value decreased from $70.23 in November to $65.96 in December, indicating that top-line growth was driven by higher transaction volume rather than larger basket sizes.

## revenue_by_source

> Which traffic source generated the most revenue?

**Check by eye:** Must say traffic_source is the user's first-touch source, and flag <Other>/(data deleted).

**Google** generated the most revenue among all traffic sources, bringing in **$104,831** (28.9% of total store revenue) across 1,620 purchase events.

- Organic search drove the vast majority of Google revenue at $95,775 (26.4% of store revenue), with paid search (`cpc`) contributing $9,056.
- Direct traffic (`(direct)`) ranked second among named sources, delivering $79,650 (22.0% share) across 1,251 purchases.
- Self-referrals from `shop.googlemerchandisestore.com` generated $46,521 (12.8% share).
- Obfuscation placeholders `<Other>` and `(data deleted)` accounted for a combined $131,163 (36.2% share).

Note: GA4 records the user's first-touch acquisition source rather than the converting session's source. Data covers November 1, 2020 through January 31, 2021.

## revenue_by_device

> How does revenue differ between mobile and desktop users?

Desktop generated **$208,815** (57.7% of total revenue), outpacing mobile which brought in **$146,768** (40.5%).

- **Volume drives desktop revenue**: Desktop users placed 3,226 orders compared to 2,355 on mobile, driven primarily by a larger user base (158,917 desktop vs 109,195 mobile users).
- **Average order value is comparable**: Desktop orders averaged $64.73 versus $62.32 for mobile.
- **Conversion efficiency is slightly higher on mobile**: Mobile sessions converted at 1.6% (yielding $1.34 revenue per user), compared to 1.5% on desktop ($1.31 revenue per user).
- **Tablets account for the remaining share**: Tablet users contributed $6,582 across 111 purchases (1.8% of revenue).

Note: Data covers November 1, 2020 through January 31, 2021 across all available events.

## most_purchased_products

> Which products generated the most purchases?

**Check by eye:** Should state whether 'purchases' means units or orders.

Ranking by revenue (the standard metric), the **Google Zip Hoodie F/C** generated the most purchases at **$13,788** across 273 units sold.

* **Google Crewneck Sweatshirt Navy** was second with **$10,714** (236 units), followed by Google Men's Tech Fleece Grey at $9,965 (134 units).
* Apparel items dominated the top revenue rankings, taking 9 of the top 10 positions.
* If measured by sales volume (units sold) instead of revenue, lower-priced items led: Google Clear Pen 4-Pack was first with 444 units ($1,376), followed by Google Laptop and Cell Phone Stickers with 416 units ($1,095).

Note: Data covers November 1, 2020 through January 31, 2021; obfuscation placeholders were excluded from product rankings.

## views_vs_purchases

> Which products had high views but relatively low purchase rates?

**Check by eye:** Must caveat that view_item events carry several items, so item 'views' are inflated; ranking is relative, not a true conversion rate.

Several high-traffic apparel products generated tens of thousands of views but recorded **0 purchases**, led by Google Women's Striped L/S with **42,142 views**.

- Google Women's Striped L/S (42,142 views), Google F/C Long Sleeve Tee Charcoal (34,275 views), Google F/C Long Sleeve Tee Ash (27,987 views), and Google Eco Tee Black (20,989 views) each recorded zero purchases.
- YouTube Women's Favorite Tee White accumulated 29,872 views but only 6 purchase events (0.0% conversion rate).
- Android Small Trace Journal Black and Google Tee Green each exceeded 30,000 views, yet resulted in just 15 and 18 purchases respectively (0.1% conversion rate each).
- For comparison, products with at least 5,000 views had an average view-to-purchase rate of 0.5%.

Note: In GA4, `view_item` events contain multiple products per event (averaging ~7), which inflates raw item view counts; view-to-purchase rates are best used for relative comparison.

## followup_chain

> What were the top 5 products by revenue?
> What about just December?
> How does that compare with November?

December's top seller, the Google Crewneck Sweatshirt Navy, grew **31.4%** month-over-month from $4,312 to $5,665, overtaking November's leader.

* **Google Canteen Bottle Black** saw the largest surge, jumping **213.1%** from $1,134 in November to $3,550 in December to enter the top five.
* Google Zip Hoodie F/C dropped 17.5% from $6,660 (where it was November's #1 item) to $5,496.
* Super G Unisex Joggers increased 15.2% (+$623) to $4,725, while Google Men's Tech Fleece Grey declined 11.1% (-$515) to $4,139.
* November's second-biggest seller, Google Badge Heavyweight Pullover Black ($6,091 in November), fell to $2,965 and dropped out of the top five.

## ambiguous

> What performed best?

**Check by eye:** Should ask what to compare (products, channels, days, ...) instead of picking one silently.

Could you clarify what you would like to evaluate performance for? For example:

1. **Top products or categories** (by revenue or units sold)
2. **Traffic acquisition channels** (by revenue, sessions, or conversion rate)
3. **Devices or countries** (by revenue or average order value)
4. **Time periods** (best-performing months or days)
