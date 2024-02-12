import streamlit as st

some_list = [1, 2, 3, 4, 5]

if "data" not in st.session_state:
    st.session_state["data"] = {
        1: 123,
        2: 456,
    }


def get_data(key: int):
    return st.session_state["data"].get(key, None)


def add_data(key: int, value: int):
    st.session_state["data"][key] = value


for e in some_list:
    result = get_data(e)
    if not result:
        new_value = st.number_input(f"Missing value for {e}", value=5)
        tmp_button = st.button("Add value to database", key=f"missing_{e}")
        if tmp_button:
            add_data(e, new_value)
            st.rerun()
        else:
            st.stop()

    st.write(e, "=", st.session_state["data"][e])
