import streamlit as st
from dotenv import load_dotenv
import pickle
from PyPDF2 import PdfReader
from streamlit_extras.add_vertical_space import add_vertical_space
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.llms import OpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.callbacks import get_openai_callback
import os
import requests
from bs4 import BeautifulSoup

# Sidebar contents
with st.sidebar:
    st.title(' ♠️ LLM Chat App ♠️ ')
    st.markdown('''
    ## About
    This app is an LLM-powered chatbot built using:
    - [Streamlit](https://streamlit.io/)
    - [LangChain](https://python.langchain.com/)
    - [OpenAI](https://platform.openai.com/docs/models) LLM model
    - [Abhishek kumar](https://github.com/Abhishek9102s) All code here
    ''')
    add_vertical_space(5)
    st.write('Made by [Abhishek kumar]')

load_dotenv()

def extract_text_from_wikipedia(link):
    response = requests.get(link)
    soup = BeautifulSoup(response.text, 'html.parser')
    paragraphs = soup.find_all('p')
    text = ' '.join([paragraph.get_text() for paragraph in paragraphs])
    return text

def main():
    st.header("Chat with PDF or Wikipedia 💬")

    # Initialize session_state if not exists
    if "session_state" not in st.session_state:
        st.session_state.session_state = {}

    # Get or create conversation in session_state
    conversation = st.session_state.session_state.get("conversation", [])
    st.session_state.session_state["conversation"] = conversation

    # Get or create cache for uploaded PDFs
    pdf_cache = st.session_state.session_state.get("pdf_cache", {})
    st.session_state.session_state["pdf_cache"] = pdf_cache

    # Upload a PDF file or provide a Wikipedia link
    option = st.radio("Select a source:", ["PDF", "Wikipedia"])
    
    if option == "PDF":
        # Upload a PDF file
        pdf_file = st.file_uploader("Upload your PDF", type='pdf')

        # Check if PDF is already in cache
        if pdf_file is not None:
            file_name = pdf_file.name
            if file_name not in pdf_cache:
                pdf_cache[file_name] = pdf_file
                st.session_state.session_state["pdf_cache"] = pdf_cache

        selected_pdf_name = st.selectbox("Select a PDF", list(pdf_cache.keys()), format_func=lambda x: x if x else "")

        selected_pdf = pdf_cache.get(selected_pdf_name)
        
        if selected_pdf:
            pdf_reader = PdfReader(selected_pdf)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
    else:
        # Accept Wikipedia link
        wikipedia_link = st.text_input("Enter Wikipedia link:")
        if wikipedia_link:
            text = extract_text_from_wikipedia(wikipedia_link)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text=text)

    store_name = selected_pdf_name[:-4] if option == "PDF" else "wikipedia"

    # Load or create VectorStore
    vector_store_path = f"{store_name}.pkl"
    if os.path.exists(vector_store_path):
        with open(vector_store_path, "rb") as f:
            VectorStore = pickle.load(f)
    else:
        embeddings = OpenAIEmbeddings()
        VectorStore = FAISS.from_texts(chunks, embedding=embeddings)

        with open(vector_store_path, "wb") as f:
            pickle.dump(VectorStore, f)

    openai_api_key = os.environ["OPENAI_API_KEY"]
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

    # Accept user questions/query
    query = st.text_input("Ask questions about your document:")

    if query:
        docs = VectorStore.similarity_search(query=query, k=3)
        llm = OpenAI(model_name='gpt-3.5-turbo')
        chain = load_qa_chain(llm=llm, chain_type="stuff")
        with get_openai_callback() as cb:
            response = chain.run(input_documents=docs, question=query)
        st.write(response)

        
if __name__ == '__main__':
    main()
