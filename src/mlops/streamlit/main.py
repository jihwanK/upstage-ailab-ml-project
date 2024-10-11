import streamlit as st
import json
import requests


def read_json():
    with open("../../../data/final/user_id2code.json", "r", encoding="utf-8") as file:
        user_id2code = json.load(file)
        return user_id2code

def check_credentials(username):
    return username in st.session_state.user_id2code

def login_page():
    st.title("올리브영 추천시스템 Login")
    username = st.text_input("Username")
    if st.button("Login"):
        if check_credentials(username):
            st.session_state.usercode = st.session_state.user_id2code[username]
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid username")

def get_recommendations(category):
    response = requests.get(f"http://127.0.0.1:8000/api/v1/recommend/{st.session_state.usercode}", timeout=10)
    result = json.loads(response.text)

    items = [ item[0] for item in result[category] ]
    imgs = [ item for item in result[f"{category}_img"] ]
    return items, imgs

def display_recommendations(title, items, imgs):
    st.subheader(title)
    print(imgs)
    items_html = ''.join([
        f'''<div class="item">
        <figure>
        <a href="https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={st.session_state.product_name2id[item]}">
        <img src={img} />
        </a>
        <figcaption>{item}</figcaption>
        </figure>
        </div>''' for item, img in zip(items, imgs)])
    st.markdown(f"""
    <div class="scrolling-wrapper">
        {items_html}
    </div>
    """, unsafe_allow_html=True)

def user_main_page():
    st.title(f"안녕하세요 {st.session_state.username}님")
    st.write("개인 맞춤형 올리브영 추천시스템에 오신걸 환영합니다 :D")

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
        vertical-align: top;
        width: 200px;
        height: 300px;
        border: 1px solid #ddd;
        margin-right: 10px;
        padding: 10px;
        text-align: center;
        font-size: 16px;
        color: green;
        box-sizing: border-box;
        text-wrap: stable;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        seen_items, seen_imgs = get_recommendations("seen")
        display_recommendations("지금까지 구매했던 제품 중 추천!!", seen_items, seen_imgs)

    with st.container(border=True):
        unseen_items, unseen_imgs = get_recommendations("unseen")
        display_recommendations("아직까지 구매하지 않았던 제품 추천!!", unseen_items, unseen_imgs)

    with st.container(border=True):
        alltime_best, alltime_img = get_recommendations("seen")
        display_recommendations("올리브영에서 가장 인기있는 제품 추천!!", alltime_best, alltime_img)

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
    if "user_id2code" not in st.session_state:
        st.session_state.user_id2code = read_json()
    main()
