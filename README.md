# AI-Powered Real Estate Property Valuation Assistant

## 1. Project Overview

The AI-Powered Real Estate Property Valuation Assistant is an intelligent application that estimates property prices using Machine Learning, Retrieval-Augmented Generation (RAG), hybrid search, and multi-agent orchestration.

The system analyzes property characteristics, retrieves historically similar properties, predicts property prices, and provides explainable valuation recommendations. It also evaluates recommendation quality, estimates valuation risk and confidence, and supports user feedback.

The application provides a React-based user interface and a FastAPI backend for interacting with the valuation pipeline.

## 2. Problem Statement

Real estate valuation involves analyzing multiple factors, including property size, construction year, overall quality, neighborhood, number of bedrooms, bathrooms, and garage facilities.

Manually identifying comparable properties and understanding how these features influence property prices can be time-consuming. Traditional prediction models may also provide numerical estimates without sufficient supporting evidence or explanations.

Therefore, an intelligent system is needed to retrieve relevant historical property records, predict property values, explain the factors influencing predictions, and provide evidence-based recommendations.

## 3. Business Objective

The primary objective is to simplify property valuation by combining Machine Learning predictions with historical comparable-property evidence.

The key objectives are:

- Estimate property prices using historical housing data.
- Retrieve similar properties using semantic and keyword-based search.
- Prioritize relevant comparable properties using metadata filtering and ranking.
- Explain predictions using SHAP feature contributions.
- Analyze historical neighborhood pricing context.
- Estimate valuation confidence, risk, and a reasonable price range.
- Validate generated recommendations using an LLM-as-Judge and DeepEval.
- Provide a user-friendly interface for property analysis.
- Incorporate user feedback to improve comparable-property ranking.

## 4. Solution Summary

The system uses the Ames Housing Dataset to train a property valuation model and build a searchable collection of historical property records.

The solution follows these steps:

1. **Property Input:** Users enter property characteristics through the React frontend.
2. **API and Validation:** FastAPI receives the request and validates the input using validation rules and guardrails.
3. **Multi-Agent Workflow:** LangGraph orchestrates the property classification, retrieval, valuation, risk analysis, and decision stages.
4. **Hybrid Retrieval:** Sentence Transformer embeddings and ChromaDB support semantic search, while BM25Okapi supports keyword-based retrieval.
5. **Result Ranking:** Reciprocal Rank Fusion (RRF) combines retrieval rankings to prioritize comparable properties.
6. **Price Prediction:** A trained Random Forest regression model predicts the property value, supported by comparable-property evidence.
7. **Explainability:** SHAP explains how individual features influence the model prediction.
8. **Risk and Confidence:** The system assesses the quality and consistency of the available evidence and produces a valuation range and confidence assessment.
9. **Recommendation Validation:** The LLM-as-Judge evaluates whether the recommendation is relevant and grounded in the available evidence. DeepEval is used to evaluate recommendation quality.
10. **Feedback and History:** SQLite stores application history and user feedback, which can influence future comparable-property ranking.

The system includes fallback mechanisms to maintain useful functionality when certain components are unavailable.

## 5. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Programming Language | Python | Backend, ML, retrieval, and evaluation |
| Frontend | React.js, Vite | User interface |
| Backend API | FastAPI | API endpoints and request handling |
| LLM | Claude via Anthropic API | LLM-as-Judge and recommendation validation |
| Embedding Model | `sentence-transformers/all-MiniLM-L6-v2` | Generate semantic embeddings |
| Vector Database | ChromaDB | Store and retrieve property embeddings |
| Keyword Retrieval | BM25Okapi (`rank-bm25`) | Keyword-based document retrieval |
| Ranking | Reciprocal Rank Fusion (RRF) | Combine semantic and keyword rankings |
| ML Model | Random Forest Regressor | Property price prediction |
| Explainability | SHAP | Explain model feature contributions |
| Agent Orchestration | LangGraph | Coordinate valuation workflow stages |
| Evaluation | DeepEval, GEval | Evaluate recommendation quality |
| Persistence | SQLite | Store feedback and application history |
| Data Processing | pandas, NumPy, scikit-learn | Data preparation and model development |
| Testing | pytest | Backend and component testing |

## 6. Programming Language

**Python** is the primary programming language for the backend and AI components.

It is used for:

- Data preprocessing and feature engineering.
- Training and evaluating the Random Forest regression model.
- Semantic embeddings and hybrid retrieval.
- API development using FastAPI.
- Workflow orchestration using LangGraph.
- Explainability using SHAP.
- Recommendation evaluation using DeepEval.
- Automated testing.

**JavaScript** is used for the React frontend and Vite-based development environment.

## 7. LLM Used

The project uses **Claude through the Anthropic API** for LLM-based recommendation validation.

The LLM-as-Judge evaluates the generated recommendation for factors such as:

- Relevance to the user's property.
- Grounding in the supplied comparable-property evidence.
- Completeness of the recommendation.
- Quality of reasoning.
- Presence of unsupported claims.

The application includes fallback handling when the primary LLM is unavailable.

The LLM is not the primary numerical price prediction model. The Random Forest model performs the property price prediction.

**Configuration:** The primary LLM model is configured through environment variables, using `claude-sonnet-4-6` as the documented default.

## 8. Embedding Model

The project uses:

`sentence-transformers/all-MiniLM-L6-v2`

This model converts property descriptions into numerical vector embeddings that represent semantic information.

These embeddings enable the system to retrieve properties with similar characteristics, even when the query wording differs.

Property descriptions can include:

- Neighborhood.
- Overall quality and condition.
- Above-ground living area.
- Basement area.
- Construction and remodeling years.
- Bedrooms and bathrooms.
- Total rooms.
- Garage characteristics.
- Lot area.

The target field `SalePrice` is kept separate from the embedding description to avoid introducing the target price directly into semantic retrieval.

The embedding model runs locally after its initial download and caching, without requiring a paid embedding API.

## 9. Vector Database

**ChromaDB** is used as the vector database.

It stores property descriptions, their embeddings, identifiers, and relevant metadata.

The retrieval pipeline uses ChromaDB for semantic similarity search and combines its results with BM25 keyword retrieval.

Metadata filters can narrow searches using available property characteristics such as neighborhood, construction year, rooms, and property size.

The vector database can be rebuilt from the prepared property data using the project's embedding-building script when required.

## 10. Frameworks and Libraries Used

### AI and Machine Learning
- scikit-learn
- pandas
- NumPy
- SHAP
- sentence-transformers

### Retrieval and RAG
- ChromaDB
- rank-bm25
- Reciprocal Rank Fusion (RRF)

### LLM and Agent Workflow
- LangGraph
- Anthropic API
- DeepEval

### Backend and Database
- FastAPI
- Pydantic
- SQLite

### Frontend
- React.js
- Vite
- npm

### Testing and Evaluation
- pytest
- DeepEval GEval

## 11. Installation Instructions

### Prerequisites

Install the following:

- Python 3.12 or a compatible version supported by the project's dependencies.
- Node.js and npm.
- Git (optional, for cloning the repository).
- An Anthropic API key for LLM-based evaluation.

### Step 1: Obtain the Project

Clone the repository or download and extract the project ZIP.

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_PROJECT_DIRECTORY>
```

If using the ZIP, open a terminal in the extracted project directory instead.

### Step 2: Create a Python Virtual Environment

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Python Dependencies

If `requirements.txt` is in the project root:

```bash
pip install -r requirements.txt
```

If the file is inside `backend/`, run:

```bash
pip install -r backend/requirements.txt
```

Use the dependency file included in the repository.

### Step 4: Configure Environment Variables

Create a `.env` file in the directory expected by the backend configuration.

Add the required variables, for example:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
PRIMARY_LLM_MODEL=claude-sonnet-4-6
DEEPEVAL_MODEL=claude-sonnet-4-6
```

Replace the placeholder with your own valid API key.

**Security:** Never commit `.env` to GitHub. Commit `.env.example` with placeholder values instead.

### Step 5: Prepare the Dataset and Model

Ensure that the Ames Housing Dataset is present in the expected `data/` directory.

If the trained model is not included, run the model training script:

```bash
python scripts/train_model.py
```

If the ChromaDB index is not included, build the embeddings and vector index:

```bash
python scripts/build_embeddings.py
```

Run these commands from the directory expected by the scripts. Check their arguments or the README instructions if your project uses a different working directory.

### Step 6: Start the FastAPI Backend

Run the backend using the module path configured in the project. For example, if `app/main.py` is inside `backend/`:

```bash
cd backend
uvicorn app.main:app --reload
```

The API is typically available at:

`http://127.0.0.1:8000`

FastAPI interactive API documentation is available at:

`http://127.0.0.1:8000/docs`

### Step 7: Start the React Frontend

Open a second terminal and navigate to the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite in the terminal.

Ensure the frontend API configuration points to the running FastAPI backend.

## 12. Environment Setup

The application uses environment variables to configure API credentials and LLM behavior.

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Authentication for the Anthropic API |
| `PRIMARY_LLM_MODEL` | Primary LLM used by the application |
| `DEEPEVAL_MODEL` | Model used for DeepEval-based evaluation |

The values above reflect the documented project configuration. Check the backend configuration files for any additional required variables.

### Environment Setup Best Practices

- Keep credentials in `.env`.
- Add `.env` to `.gitignore`.
- Provide `.env.example` for other developers.
- Never hardcode API keys in Python or JavaScript source files.
- Do not commit virtual environments, dependency caches, or generated database files unnecessarily.
- Keep the dataset, model artifacts, and scripts required to run the application.
- Rebuild generated embeddings when the vector database is not included.

## 13. Evaluation and Testing

The project includes testing and evaluation components.

- **Model evaluation:** Assess the regression model using appropriate regression metrics.
- **Retrieval evaluation:** Check the relevance and ranking of retrieved comparable properties.
- **LLM-as-Judge:** Validate generated recommendations against evidence and reasoning criteria.
- **DeepEval GEval:** Evaluate property recommendation quality using defined criteria.
- **Automated tests:** Use pytest to test core functionality, retrieval, explainability, and judge behavior.

DeepEval evaluates recommendation quality; it does not train the Random Forest model or directly predict property prices.

## 14. Limitations

- The model is trained using the Ames Housing Dataset, which represents a specific US housing market and may not generalize directly to other regions.
- Valuation quality depends on the dataset, feature quality, model performance, and relevance of retrieved comparables.
- The confidence and risk assessments are evidence-based heuristics rather than calibrated probabilities from a separately trained risk model.
- Historical neighborhood price differences are descriptive and should not be interpreted as causal effects.
- LLM-based evaluation requires appropriate configuration and may incur API costs.

## 15. Conclusion

The AI-Powered Real Estate Property Valuation Assistant combines machine learning, hybrid RAG, multi-agent workflow orchestration, explainability, and recommendation evaluation in a single application.

By combining numerical price prediction with historical comparable-property evidence and feature-level explanations, the system provides a more transparent and evidence-informed property valuation workflow.
