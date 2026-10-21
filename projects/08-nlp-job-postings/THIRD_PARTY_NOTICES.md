# Third-party materials

- **SEEK samples and cohort metadata:** PromptCloud / DataStock, through two
  Kaggle version-1 datasets. Publisher declaration: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
  Modifications: HTML/NFKC/whitespace normalization, conflict filtering,
  duplicate merging, archived cohort selection and fixed split metadata.
- **SkillSpan tokens, labels and derived phrases:** Mike Zhang, Kristian
  Nørgaard Jensen, Sif Dam Sonniks, Barbara Plank (2022).
  [Paper and citation](https://aclanthology.org/2022.naacl-main.366/).
  Data-card declaration: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  Modifications: lossless CSV conversion, sentence IDs, deterministic sample
  selection, exclusion of evaluation sentences repeated in training, and
  derived prediction/span statistics. Upstream code's MIT license does not
  replace the dataset's attribution requirement.
- **MiniLM:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2),
  pinned revision in METHODS.md. Model files are downloaded by users and are
  not redistributed in this repository. Consult its model card for terms.
- **JobStreet:** Mohamad Azrai bin Mahadan. The pinned card has conflicting
  Apache-2.0 and CC BY 4.0 statements. This release redistributes no JobStreet
  descriptions and does not choose one of those declarations as definitive.
- **Coursework:** team attribution is preserved in CONTRIBUTIONS.md. Original
  Word files are not redistributed by this integration.

The integration's MIT license covers its implementation scope only. Third-party
data and model terms remain separate.
