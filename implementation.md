# Vastu House Layout Generation Pipeline

This project is an autonomous, multi-agent AI pipeline that automatically generates geometrically valid, mathematically verified 2D house layouts based on natural language constraints (specifically optimized for Vastu compliance).

## Architecture

The pipeline consists of a multi-stage approach using Large Language Models (LLMs) combined with the Z3 SMT solver for absolute mathematical verification.

1. **Stage 1 (Footprint Generation)**: Computes the 2D footprint of the house inside a given plot boundary based on Local Setback Constraints (SBC) and Custom Rules.
2. **Stage 2 (Ground Floor Packing)**: An LLM Agent (Coder) generates Python Z3 code to optimally pack rooms into the footprint according to minimum dimensions and Vastu constraints. A Mentor Agent reviews failed Z3 compilations and provides corrections until mathematically satisfiable.
3. **Stage 3 (Upper Floor Generation)**: Generates the First Floor rooms tightly constrained within the boundary of the Ground Floor.

## How to Clone and Run

1. **Clone the repository**:
   ```bash
   git clone https://github.com/amaze18/LLMOauth.git
   cd LLMOauth
   ```

2. **Set up a Virtual Environment**:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up API Keys**:
   Create a `.env` file in the root directory and add your API Keys:
   ```env
   GROQ_API_KEY=your_groq_api_key
   # Optional: MLflow telemetry
   USE_MLFLOW=True
   ```

5. **Start the Local Web Server**:
   ```bash
   python flask_app.py
   ```

6. **Generate Layouts**:
   Open your browser to `http://127.0.0.1:5000`. You will be presented with a visual canvas. 
   Click **Generate** to watch the AI agents autonomously iterate, compile Z3 math constraints, and construct the House Layout. The final output is rendered in the UI and downloadable as a `.dxf` CAD file!
