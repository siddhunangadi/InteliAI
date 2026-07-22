"""Thin requests wrapper around the FastAPI backend, shared by every page."""

import os

import requests
import streamlit as st

DEFAULT_BASE_URL = os.environ.get("RAG_API_BASE_URL", "http://localhost:8000")


def base_url() -> str:
    return st.session_state.get("api_base_url", DEFAULT_BASE_URL)


def _headers() -> dict:
    api_key = st.session_state.get("api_key") or os.environ.get("RAG_API_KEY")
    return {"X-API-Key": api_key} if api_key else {}


def get(path: str, **kwargs) -> requests.Response:
    return requests.get(f"{base_url()}{path}", headers=_headers(), timeout=30, **kwargs)


def post(path: str, **kwargs) -> requests.Response:
    return requests.post(f"{base_url()}{path}", headers=_headers(), timeout=120, **kwargs)


def delete(path: str, **kwargs) -> requests.Response:
    return requests.delete(f"{base_url()}{path}", headers=_headers(), timeout=30, **kwargs)
