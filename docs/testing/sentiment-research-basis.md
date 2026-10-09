# Research supporting Thesis sentiment analysis

9 October 2026. Current pitch approach: use published research to explain the rationale for sentiment analysis. The owner deferred running the proposed experiment for now. This material supports the method's motivation; it supplies no measured Thesis accuracy, investment return or user benefit.

## Three papers for the main slide

| Part of Thesis | Research and finding | Connection to our approach |
| --- | --- | --- |
| Company news | Tetlock, Saar-Tsechansky and Macskassy (2008), *More Than Words: Quantifying Language to Measure Firms' Fundamentals*, Journal of Finance 63, 1437–1467. Negative language in company news forecast weaker earnings and related to brief price underreaction, particularly in stories about fundamentals. [Author institution](https://business.columbia.edu/faculty/research/more-words-quantifying-language-measure-firms-fundamentals) | Financial language can contain information worth extracting alongside numerical company data. This study used quantitative text measures, not Thesis's model or prompt. |
| Investor discussion | Chen, De, Hu and Hwang (2014), *Wisdom of Crowds: The Value of Stock Opinions Transmitted Through Social Media*, Review of Financial Studies 27, 1367–1403. Opinions in investment articles and reader comments predicted subsequent returns and earnings surprises in the studied community. [Publisher abstract](https://academic.oup.com/rfs/article-abstract/27/5/1367/1581938) | Supports examining investor discussion as an additional information source. Results from that community do not establish equivalent performance on Reddit or Hacker News. |
| Language model analysis | Lopez-Lira and Tang (2026), *Can ChatGPT Forecast Stock Price Movements? Return Predictability and Large Language Models*, Journal of Financial Economics 184, 104335. Assessments of post-training-cutoff headlines predicted market reactions and subsequent drift, with stronger effects for smaller stocks and negative news. [Publisher](https://www.sciencedirect.com/science/article/pii/S0304405X26001066), [full author version revised in 2025](https://arxiv.org/html/2304.07619v6) | Supports using an LLM to extract financial meaning from news. Its price-impact task differs from Thesis's source-tone task; the result does not validate our exact pipeline. |

These connections are an application of the research to Thesis's design, not findings made by the papers about Thesis. Published evidence supports the relevance of the inputs and the plausibility of the analysis approach. It does not guarantee an investment advantage.

## Slide copy

### A research backed approach to reading financial sentiment

- **News contains useful signals.** Research links company-specific news language with subsequent earnings and market reactions. [Tetlock et al., 2008](https://business.columbia.edu/faculty/research/more-words-quantifying-language-measure-firms-fundamentals)
- **Investor discussion can add information.** Research finds predictive information in investment articles and reader comments. [Chen et al., 2014](https://academic.oup.com/rfs/article-abstract/27/5/1367/1581938)
- **Language models can interpret financial news.** Research demonstrates predictive information in LLM assessments of headlines. [Lopez-Lira and Tang, 2026](https://www.sciencedirect.com/science/article/pii/S0304405X26001066)

Thesis builds on this research to organise company-specific sentiment from news and discussion, with inspectable source evidence.

Footer: Published findings support the approach. Thesis-specific effectiveness has not yet been independently validated.

## Speaker note

Our premise has empirical support: company news and investor opinions can contain financially relevant information, and language models can help interpret it. Thesis brings these ideas into a research workflow where users can inspect the original evidence. We have not yet measured our own predictive performance or user benefit.

## Additional method reference for the appendix

[Tang et al. (2023), *FinEntity: Entity-level Sentiment Classification for Financial Texts*, EMNLP](https://aclanthology.org/2023.emnlp-main.956/) provides company/entity-level financial sentiment annotations and model benchmarks. It is particularly relevant to judging the attitude toward the researched company when a text mentions several companies. Its positive/neutral/negative task does not independently validate Thesis's mixed/unclear handling, evidence guards or five-group threshold.

## Claims to keep separate

“Research-backed approach” describes the evidence above. “Thesis predicts stock prices accurately,” “Thesis improves returns,” “Thesis saves research time” and a numerical accuracy claim require our own suitable evaluation. The approximately 90% result in the LLM paper concerns portfolio-days for the non-tradable initial reaction; do not present it as individual-stock prediction accuracy or a Thesis metric.

Thesis's differentiation is a product proposition: connecting news and discussion readings to inspectable evidence and saved company research. These citations do not establish product uniqueness, commercial demand or a proprietary scientific discovery. The existing developer-reference checks remain engineering evidence with their recorded limitations.

The earlier [experiment protocol](sentiment-effectiveness-study.md) remains available for future validation. No experiment, paid Thesis model run, source acquisition, watch activation or pitch-deck file edit accompanies this literature-based change.
