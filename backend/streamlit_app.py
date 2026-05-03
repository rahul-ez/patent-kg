import streamlit as st
from src.nlp.pipeline import process_user_query, prepare_embedding_input

def main():
    st.set_page_config(page_title="NLP Pipeline Demo", page_icon="🧬", layout="centered")
    
    st.title("🧬 Patent NLP Pipeline Demo")
    st.write("Demonstration of the text preprocessing, keyword extraction, and NER pipeline.")
    
    # Initialize session state for sample input
    if "user_input" not in st.session_state:
        st.session_state["user_input"] = ""
    
    # Sample Input Button
    sample_text = "This invention provides an advanced system for autonomous drone navigation utilizing neural networks and LiDAR sensors. Apple Inc. developed this novel architecture in California to improve pathfinding efficiently in urban environments."
    
    if st.button("Load Sample Input"):
        st.session_state["user_input"] = sample_text
        
    user_input = st.text_area(
        "Enter Patent Description or Query:", 
        value=st.session_state["user_input"], 
        height=150
    )
    
    if st.button("Run Pipeline"):
        if not user_input.strip():
            st.warning("Please enter some text to process.")
            return
            
        with st.spinner("Processing NLP Pipeline..."):
            # Execute Pipeline
            processed_data = process_user_query(user_input)
            embedding_string = prepare_embedding_input(processed_data)
            
            st.success("Processing Complete!")
            
            st.divider()
            
            # --- 1. Cleaned Text ---
            st.subheader("🧹 Cleaned Text")
            st.info(processed_data.get("clean_text", ""))
            
            # --- 2. Extracted Keywords ---
            st.subheader("🔑 Extracted Keywords")
            keywords = processed_data.get("keywords", [])
            if keywords:
                for kw in keywords:
                    st.markdown(f"- **{kw}**")
            else:
                st.write("No technical concepts found.")
                
            # --- 3. Extracted Entities ---
            st.subheader("🏛️ Extracted Entities")
            entities = processed_data.get("entities", [])
            if entities:
                st.json(entities)
            else:
                st.write("No named entities extracted.")
                
            # --- 4. Final Embedding Input String ---
            st.subheader("🔗 Final Embedding Input String")
            st.code(embedding_string, language="text")

if __name__ == "__main__":
    main()
