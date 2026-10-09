# Company logo images

Downloaded unmodified on 9 October 2026 from Financial Modeling Prep's [company image route](https://site.financialmodelingprep.com/developer/docs/company-image-api). Each request returned HTTP 200 and `image/png` without credentials or redirects. The provider documents this as a legacy route; future availability is not guaranteed.

| Company | Original URL | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Broadcom | https://financialmodelingprep.com/image-stock/AVGO.png | 17025 | `0afd68b45dbefb8ad9e75bc9cda3898a3d75ab026dde215cfe9def48d4fb4a41` |
| NVIDIA | https://financialmodelingprep.com/image-stock/NVDA.png | 11180 | `65adfc123c82dd816d8bebeaded5d0bdd72a4a799d1c0e23d310eaf6e2c457e6` |
| Fabrinet | https://financialmodelingprep.com/image-stock/FN.png | 2210 | `20b3a22f106981484827e99ec0d5a94192cbfc1ee0715772954d85f4c299ad1e` |
| Marvell Technology | https://financialmodelingprep.com/image-stock/MRVL.png | 3197 | `c6f5463cceacf32245f2d6488edd22c20567a72fd209aecfe9a5ea4b53edc26d` |

Marvell's unmodified mark is white on transparent. Its avatar uses a dark frame so the mark remains visible.

The current workspace images are bundled by Vite. Other registered SEC companies use the same HTTPS image route when displayed, with no referrer. Pending or failed images retain the company initial. Fictional recorded companies retain their initials without an external image request. These company marks are used to identify the issuer in the company list and header.
