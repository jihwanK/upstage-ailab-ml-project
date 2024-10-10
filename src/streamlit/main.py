import streamlit as st
import json


def read_json():
    with open("../../data/final/user_id2code.json", "r", encoding="utf-8") as file:
        id2code = json.load(file)
        return id2code

def check_credentials(username):
    if username in st.session_state.id2code:
        st.session_state.usercode = st.session_state.id2code[username]
        return True
    else:
        return False

def login_page():
    st.title("Login Page")
    username = st.text_input("Username")
    if st.button("Login"):
        if check_credentials(username):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid username")

def get_recommendations(username, category):
    items = [
        f"{category} Item {i}" for i in range(1, 11)
    ]
    return items

def display_recommendations(title, items):
    st.subheader(title)
    items_html = ''.join([f'<div class="item">{item}</div>' for item in items])
    st.markdown(f"""
    <div class="scrolling-wrapper">
        {items_html}
    </div>
    """, unsafe_allow_html=True)

def user_main_page():
    st.title(f"Welcome, {st.session_state.username}!")
    st.write("Here are your personalized recommendations:")

    # Custom CSS for horizontal scrolling
    st.markdown("""
    <style>
    .scrolling-wrapper {
        overflow-x: auto;
        white-space: nowrap;
        -webkit-overflow-scrolling: touch;
        padding: 10px 0;
    }
    .item {
        display: inline-block;
        width: 200px;
        height: 100px;
        border: 1px solid #ddd;
        margin-right: 10px;
        text-align: center;
        line-height: 100px;
        background-color: #f9f9f9;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        books = get_recommendations(st.session_state.username, "Book")
        display_recommendations("지금까지 구매했던 제품 중 추천!!", books)

    with st.container(border=True):
        movies = get_recommendations(st.session_state.username, "Movie")
        display_recommendations("아직까지 구매하지 않았던 제품 추천!!", movies)

    with st.container(border=True):
        products = get_recommendations(st.session_state.username, "Product")
        display_recommendations("올리브영에서 가장 인기있는 제품 추천!!", products)

    if st.button("Refresh Recommendations"):
        st.rerun()

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        user_main_page()
    else:
        login_page()

if __name__ == "__main__":
    if "id2code" not in st.session_state:
        st.session_state.id2code = read_json()
    main()
