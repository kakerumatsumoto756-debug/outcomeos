# OutcomeOS — Reviewer questions and concise answers

**Q: What is OutcomeOS in one sentence?**
A: A collaborative workspace that compares team forecasts with Panta market signals and measures accuracy after events resolve.

**Q: Is OutcomeOS a prediction market?**
A: No. It is a decision-learning layer built around market data. The underlying contracts exist in Panta's ecosystem.

**Q: Does this product run its own smart contract?**
A: No. It integrates Panta's Solana-native API for market discovery and quotes; no OutcomeOS contract is deployed.

**Q: Where does Panta fit in the core experience?**
A: Users discover a market, review its question and quotes, connect relevant contracts to their own decision room, and compare the time-series signal with team forecasts and outcomes.

**Q: Why would teams use this instead of a trading site?**
A: The key workflow is decision memory, recorded evidence, team calibration, and retrospective learning—not execution of trades.

**Q: Is the YES price equivalent to a 52% chance?**
A: Not necessarily. Market prices are observations shaped by liquidity, spreads, fees, and market rules; OutcomeOS labels them as prices and treats calibration cautiously.

**Q: Does it use AI to predict the future?**
A: Not in this release. Development was substantially assisted by AI tools, but the shipped product is a deterministic decision and market-data application. We do not claim a trained model or measured uplift.

**Q: Is it free to use?**
A: The beta has no integrated subscription billing. A paid team plan is a future commercial hypothesis. API/hosting costs can vary by provider and are not guaranteed to remain free.

**Q: Do users connect a wallet or trade?**
A: No. This is a read-only integration and does not transmit orders, custody funds, or sign on-chain transactions.

**Q: How are outcomes assessed?**
A: Forecasts are paired with documented resolution results; Brier scoring provides feedback on probabilistic accuracy. Synthetic or hypothetical scores must be labeled as tests.

**Q: What is verified?**
A: Local app/API tests passed (33 tests in the v1.3 test report) and an earlier local screenshot showed 30 live market listings. The public cloud deployment, new Panta key and persistent hosted DB require separate live verification.

**Q: Who is on the team?**
A: [FOUNDERS SHOULD FILL THEIR ACTUAL TEAM DETAILS HERE]. Do not imply unconfirmed collaborators.

**Q: What are your customers and traction?**
A: Early target users are founders and research/product teams. Customer demand, retention, and revenue are not yet verified; pilot validation is the next step.

**Q: Was AI involved in development?**
A: Yes, ChatGPT substantially assisted with code generation, architecture, documentation, and tests. The founder should describe their own role accurately and disclose other meaningful contributors.
