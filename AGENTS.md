# Notes for AI coding agents

- Deals live in `deals.yml`. Never edit the generated tables in `README.md` by hand.
- Text between `<!-- NAME:START -->` and `<!-- NAME:END -->` markers in `README.md` is generated. Everything outside the markers is hand-written.
- After changing `deals.yml`, run `python scripts/build_readme.py` (needs `pyyaml`), then `python scripts/build_readme.py --check`.
- Required deal fields: `name`, `domain`, `url` (https), `description` (one line, no `|`), `offer`, `status` (`live` | `soon` | `expired`). Optional: `code`, `valid`, `logos`.
- Update `last_updated` in `deals.yml` when you change deals.
- Don't invent discounts or coupon codes. If the offer isn't confirmed, use `status: soon`.
- Work on the `dev` branch. `main` is updated only through reviewed pull requests.
