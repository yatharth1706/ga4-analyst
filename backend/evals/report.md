# Golden question results

| Case | Result | Key numbers | Ungrounded numbers | Queries | Time |
|---|---|---|---|---|---|
| total_users | pass | users: answer | none | 2 | 46s |
| top_products_revenue | pass | #1 Google Zip Hoodie F/C revenue: answer | none | 1 | 23s |
| revenue_over_time | pass | Nov 2020 revenue: answer<br>Dec 2020 revenue: answer<br>Jan 2021 revenue: answer | 64.3 | 2 | 45s |
| nov_vs_dec | pass | Nov revenue: answer<br>Dec revenue: answer | none | 2 | 38s |
| revenue_by_source | pass | google / organic revenue: answer | 131,163, 36.2 | 2 | 42s |
| revenue_by_device | pass | desktop revenue: answer<br>mobile revenue: answer | 1.6, 1.5 | 1 | 25s |
| most_purchased_products | pass | #1 Google Clear Pen 4-Pack units: answer | none | 3 | 55s |
| views_vs_purchases | manual | — | 0.6 | 4 | 72s |
| followup_chain | pass | Crewneck Sweatshirt Navy, Dec: answer<br>Crewneck Sweatshirt Navy, Nov: answer | 17.5, 11.1 | 4 | 73s |
| ambiguous | manual | — | none | 0 | 4s |

## total_users

> How many users visited the store?

A total of **270,154** unique users visited the store across **360,129** sessions.

- First-time visitors made up 257,314 of all unique users.
- December 2020 saw the highest monthly traffic with 104,315 active users.
- January 2021 followed with 94,790 active users, while November 2020 recorded 79,421 active users.

Note: Data covers the entire available dataset range from November 1, 2020 through January 31, 2021.

## top_products_revenue

> What were the top 10 products by revenue?

The top-earning product was the Google Zip Hoodie F/C, generating **$13,788** in revenue across **273** units sold.

- Google Crewneck Sweatshirt Navy followed in second with $10,714 (236 units), and Google Men's Tech Fleece Grey placed third with $9,965 (134 units).
- Outerwear and fleece apparel accounted for all top 10 spots.
- Super G Unisex Joggers drove the highest volume within the top 10, totaling 308 units ($9,529).

Note: Based on all available data from November 1, 2020 to January 31, 2021, excluding obfuscated placeholder items.

## revenue_over_time

> How did revenue change over time?

Total store revenue peaked in December 2020 at **$160,555** before falling by **64.3%** in January 2021 to $57,350.

- November 2020 generated $144,260 across 2,054 orders, then grew 11.3% in December to 2,434 orders.
- Weekly revenue peaked during the week of December 7, 2020, reaching $59,865.
- Average order value decreased each month, falling from $70.23 in November to $65.96 in December, and down to $47.63 in January.
- Weekly sales dropped sharply after mid-December, suggesting a post-holiday seasonal contraction.

Note: The data covers the available three-month window from November 1, 2020 through January 31, 2021.

## nov_vs_dec

> Compare revenue between November and December.

December 2020 revenue reached **$160,555**, an 11.3% increase of **$16,295** over November 2020's **$144,260**.

- Order volume rose 18.5% from 2,054 to 2,434 purchases, which drove the overall revenue gain.
- Average order value decreased from $70.23 in November to $65.96 in December.
- December revenue was heavily concentrated in the first half of the month, peaking at $11,509 on December 16 before trailing off.
- November revenue peaked toward the end of the month, reaching its high of $11,990 on November 30.

## revenue_by_source

> Which traffic source generated the most revenue?

**Check by eye:** Must say traffic_source is the user's first-touch source, and flag <Other>/(data deleted).

**Google** was the top traffic source, generating **$104,831** (28.9% of total revenue) across 1,620 purchase events between November 1, 2020, and January 31, 2021.

* **google / organic** accounted for the vast majority of Google's volume with $95,775 (26.4% of total revenue), while google / cpc added $9,056 (2.5%).
* **(direct)** was the next largest named source, contributing $79,650 (22.0%) from 1,251 purchase events.
* **shop.googlemerchandisestore.com** referrals generated $46,521 (12.8%) across 701 purchases.
* Obfuscated categories **`<Other>`** and **`(data deleted)`** combined for $131,163 (36.2% of total revenue).

Note: This attribution is based on the user's first-touch acquisition source rather than the session that converted.

## revenue_by_device

> How does revenue differ between mobile and desktop users?

Desktop users drove **$208,815** (57.7% of total revenue) compared to **$146,768** (40.5%) from mobile users.

- **Order volume:** Desktop generated 3,226 purchases (56.7% of orders) versus 2,355 purchases (41.4%) on mobile.
- **Average order value:** Desktop purchasers spent slightly more per transaction, with an AOV of $64.73 compared to $62.32 on mobile.
- **Conversion efficiency:** Mobile recorded a slightly higher session conversion rate (1.6% vs 1.5% on desktop), suggesting desktop's higher overall revenue was driven by larger traffic volume (208,942 vs 143,185 sessions) rather than superior conversion efficiency.
- **Tablet share:** Tablets contributed the remaining $6,582 (1.8% of total revenue) across 111 orders.

## most_purchased_products

> Which products generated the most purchases?

**Check by eye:** Should state whether 'purchases' means units or orders.

Ranking by revenue (the standard ecommerce metric), the Google Zip Hoodie F/C generated the most sales at **$13,788** across 242 purchase events.

- Google Crewneck Sweatshirt Navy was second in revenue with **$10,714**, followed by Google Men's Tech Fleece Grey ($9,965).
- By transaction frequency, Super G Unisex Joggers appeared in the most purchases (269 orders; $9,529).
- By total units sold, lower-cost items led, topped by the Google Clear Pen 4-Pack with **444** units.

Note: Data covers November 1, 2020 to January 31, 2021. Obfuscation placeholders such as `<Other>` were excluded from the product rankings.

## views_vs_purchases

> Which products had high views but relatively low purchase rates?

**Check by eye:** Must caveat that view_item events carry several items, so item 'views' are inflated; ranking is relative, not a true conversion rate.

Among heavily viewed items (over 20,000 views), apparel products such as **Google Women's Striped L/S** (42,142 views) and **Google F/C Long Sleeve Tee Charcoal** (34,275 views) recorded **0 purchases**, falling well below the catalog baseline purchase rate of 0.6%.

* **Zero-conversion apparel:** Four high-traffic shirts had 0 purchases despite substantial exposure: Google Women's Striped L/S (42,142 views), Google F/C Long Sleeve Tee Charcoal (34,275 views), Google F/C Long Sleeve Tee Ash (27,987 views), and Google Eco Tee Black (20,989 views).
* **Lowest-converting active sellers:** YouTube Women's Favorite Tee White logged 29,872 views but only 6 purchases (under 0.1% purchase rate), followed by Android Small Trace Journal Black with 30,471 views and 15 purchases (0.1%).
* **Other underperforming staples:** Google Tee Green (31,578 views, 18 purchases, 0.1%) and Android Large Trace Journal Black (32,257 views, 25 purchases, 0.1%) also showed weak conversion.

Note: In GA4, `view_item` events often contain multiple items per event payload, which inflates per-product view counts. These view-to-purchase ratios should be used for relative comparison rather than absolute conversion rates.

## followup_chain

> What were the top 5 products by revenue?
> What about just December?
> How does that compare with November?

Compared to November, December’s top five products saw mixed trends: three grew and two declined, led by a **213.1% revenue surge** for the **Google Canteen Bottle Black**.

- **Google Crewneck Sweatshirt Navy** rose **31.4%** from $4,312 (96 units) in November to $5,665 (124 units), taking the #1 spot.
- **Google Canteen Bottle Black** saw the largest increase, jumping from $1,134 (57 units) to $3,550 (180 units).
- **Super G Unisex Joggers** grew 15.2% from $4,102 (133 units) to $4,725 (153 units).
- **Google Zip Hoodie F/C** and **Google Men's Tech Fleece Grey** declined 17.5% (down from $6,660) and 11.1% (down from $4,654) respectively, despite the Hoodie being November’s best seller.

## ambiguous

> What performed best?

**Check by eye:** Should ask what to compare (products, channels, days, ...) instead of picking one silently.

Could you clarify what you would like to see the top performers for?

1. **Products** (by revenue or units sold)
2. **Traffic channels** (by first-touch revenue or sessions)
3. **Countries / regions** (by revenue)
4. **Time periods** (best days or months)
