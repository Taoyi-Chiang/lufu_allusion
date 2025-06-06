# Workflow
```mermaid
---
flowchart TD
  subgraph Preprocessing["Preprocessing"]
    A1["origin_text.txt"]
    A2["compared_text.txt"]
    A3["clean_compared_text.txt"]
    B1["origin_text.json"]
    B2["origin_text_ckip.json"]
  end

  subgraph subGraph1["Allusion Matching and Annotation"]
    C1["sentence_allusion.json"]
    C2["term_allusion.json"]
    D1["direct_allusion.csv"]
    E1["integrated_allusion_database.csv"]
  end

  subgraph subGraph2["Annotated Database and Text Structuring"]
    E2["annotated_allusion_database.csv"]
    F1["network"]
    F2["annotated_text.xml"]
  end

  A1 --> P1{P1} --> B1
  A2 --> P2{P2} --> A3
  A3 --> P3{P3} --> C1
  A3 --> P4{P4} --> C2
  B1 --> P5{P5} --> B2
  B1 --> P6{P6} --> C1
  B2 --> P7{P7} --> C2
  C1 --> P8{P8} --> C2
  C2 --> P9{P9} --> D1
  D1 --> P10{P10} --> E1
  E1 --> P11{P11} --> E2
  E2 --> P12{P12} --> F1
  E2 --> P13{P13} --> F2
```
