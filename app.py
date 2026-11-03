"""RS Matrix v8 — fixed ticker hover, compact chart, sortable leader tables and shared watchlist.
Public daily-data research tool; does not promise consolidated real-time quotes.
"""
import html
import io
import math
import re
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
from urllib.parse import quote, urlencode

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="RS MATRIX | Sector Leadership", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

# ---------- Theme / design ----------
BG = "#0b1018"
PANEL = "#131b26"
LINE = "#253142"
MUTED = "#97a6b9"
GREEN = "#24bd76"
RED = "#f05256"
AMBER = "#efbd5e"

st.markdown("""
<style>
:root{color-scheme:dark;--background-color:#0b1018;--secondary-background-color:#131b26;--text-color:#ecf2f8;--primary-color:#26c982}
html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"]{background:#0b1018!important;color:#ecf2f8!important}
[data-testid="stSidebar"], [data-testid="stSidebarContent"]{background:#111925!important}
[data-testid="stMainBlockContainer"]{max-width:1720px!important;padding-top:1.1rem!important;padding-left:2.2rem!important;padding-right:2.2rem!important}
h1,h2,h3,p,label,span{color:inherit}
[data-testid="stMarkdownContainer"] p{line-height:1.45}
[data-testid="stMetric"]{background:#141e2a;border:1px solid #253142;border-radius:10px;padding:12px 15px}
[data-testid="stMetricLabel"]{color:#9cacc1!important}
[data-testid="stMetricValue"]{color:#eaf2fa!important;font-weight:700}
[data-testid="stSelectbox"]>div>div, [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input{background:#172231!important;color:#eaf2fa!important;border-color:#304154!important}

/* === Accessibility: force readable foreground for ALL Streamlit form widgets. ===
   The prior patch styled the control background but missed the visible selected
   value in newer BaseWeb select widgets. Streamlit may portal menus to document
   root, so popover selectors must not be scoped to stSelectbox. */
:root, body, [data-testid="stAppViewContainer"] {
  --rsm-control-foreground: #E6EDF5;
  --rsm-control-label: #C8D5E5;
  --rsm-control-secondary: #A6B7C9;
  --rsm-control-background: #172231;
  --rsm-control-border: #41546B;
}

/* Labels, including inputs that Streamlit renders with internal markdown. */
[data-testid="stSelectbox"] label,
[data-testid="stMultiSelect"] label,
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stNumberInput"] label,
[data-testid="stDateInput"] label,
[data-testid="stTimeInput"] label,
[data-testid="stSelectSlider"] label,
[data-testid="stSlider"] label,
[data-testid="stRadio"] label,
[data-testid="stCheckbox"] label,
[data-testid="stSegmentedControl"] label,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] *,
[data-testid="stSelectbox"] label *,
[data-testid="stMultiSelect"] label * {
  color: var(--rsm-control-label) !important;
  -webkit-text-fill-color: var(--rsm-control-label) !important;
  opacity: 1 !important;
}

/* Outer field surface + selectable values: handle div, p, span and input. */
[data-testid="stSelectbox"] [data-baseweb="select"],
[data-testid="stMultiSelect"] [data-baseweb="select"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div,
[data-testid="stTextInput"] [data-baseweb="input"] > div,
[data-testid="stTextArea"] [data-baseweb="textarea"] > div,
[data-testid="stNumberInput"] [data-baseweb="input"] > div,
[data-testid="stDateInput"] [data-baseweb="input"] > div,
[data-testid="stTimeInput"] [data-baseweb="input"] > div {
  background-color: var(--rsm-control-background) !important;
  border-color: var(--rsm-control-border) !important;
  color: var(--rsm-control-foreground) !important;
  opacity: 1 !important;
}

/* Selected dropdown value, including Streamlit's Markdown-formatted selections.
   Explicitly set fill color because WebKit can retain the system light theme. */
[data-testid="stSelectbox"] [data-baseweb="select"] *,
[data-testid="stMultiSelect"] [data-baseweb="select"] *,
[data-testid="stSelectbox"] [role="combobox"],
[data-testid="stMultiSelect"] [role="combobox"],
[data-testid="stSelectbox"] [role="combobox"] *,
[data-testid="stMultiSelect"] [role="combobox"] *,
[data-testid="stSelectbox"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMultiSelect"] [data-testid="stMarkdownContainer"] p,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input,
[data-testid="stSelectSlider"] [data-baseweb="slider"] *,
[data-testid="stRadio"] label p,
[data-testid="stCheckbox"] label p,
[data-testid="stSegmentedControl"] button {
  color: var(--rsm-control-foreground) !important;
  -webkit-text-fill-color: var(--rsm-control-foreground) !important;
  opacity: 1 !important;
}

/* Specifically catch disabled controls, which Streamlit grays out aggressively.
   Preserve a subtle difference while keeping the selected value legible. */
[data-testid="stSelectbox"] [aria-disabled="true"],
[data-testid="stSelectbox"] [aria-disabled="true"] *,
[data-testid="stMultiSelect"] [aria-disabled="true"],
[data-testid="stMultiSelect"] [aria-disabled="true"] * {
  color: var(--rsm-control-label) !important;
  -webkit-text-fill-color: var(--rsm-control-label) !important;
  opacity: 0.94 !important;
}

/* Focus ring and dropdown chevrons. */
[data-testid="stSelectbox"] svg,
[data-testid="stMultiSelect"] svg,
[data-testid="stSelectSlider"] svg {
  color: var(--rsm-control-secondary) !important;
  fill: currentColor !important;
  opacity: 1 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"]:focus-within,
[data-testid="stMultiSelect"] [data-baseweb="select"]:focus-within {
  outline: 1px solid #5EACD7 !important;
  border-radius: 9px;
}

/* Dropdown popover lives outside the select control. Target its items and
   any markdown nodes, including currently-selected and hovered options. */
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [role="option"],
[data-baseweb="popover"] [data-baseweb="menu"],
[data-baseweb="popover"] [data-baseweb="menu"] > div,
[data-baseweb="menu"] [role="option"] {
  background-color: var(--rsm-control-background) !important;
  color: var(--rsm-control-foreground) !important;
}
[data-baseweb="popover"] [role="option"] *,
[data-baseweb="popover"] [data-baseweb="menu"] *,
[data-baseweb="menu"] [role="option"] *,
[role="listbox"] [role="option"],
[role="listbox"] [role="option"] * {
  color: var(--rsm-control-foreground) !important;
  -webkit-text-fill-color: var(--rsm-control-foreground) !important;
  opacity: 1 !important;
}
[data-baseweb="popover"] [aria-selected="true"],
[data-baseweb="popover"] [role="option"]:hover,
[role="listbox"] [aria-selected="true"],
[role="listbox"] [role="option"]:hover {
  background-color: #2C4055 !important;
}

/* Placeholders must be distinguishable from selected values, not invisible. */
[data-testid="stSelectbox"] input::placeholder,
[data-testid="stMultiSelect"] input::placeholder,
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder,
[data-testid="stNumberInput"] input::placeholder {
  color: var(--rsm-control-secondary) !important;
  -webkit-text-fill-color: var(--rsm-control-secondary) !important;
  opacity: 1 !important;
}

[data-testid="stCheckbox"] label,[data-testid="stRadio"] label{color:#dce6f2!important}
button[kind="primary"]{background:#22ab73!important;border-color:#22ab73!important;color:#08120d!important}
/* Dark surfaces for every data list, toolbar, header and editable grid.
   Streamlit renders its spreadsheet on canvas: theme config + dataframe Styler
   (see dark_table helper) both supply dark cell backgrounds. */
[data-testid="stDataFrame"], [data-testid="stTable"],
[data-testid="stDataEditor"], [data-testid="stDataFrame"] > div,
[data-testid="stDataFrame"] canvas, [data-testid="stDataEditor"] canvas,
[data-testid="stTable"] table, [data-testid="stTable"] th,
[data-testid="stTable"] td {background-color:#131b26!important;color:#e6edf5!important;border-color:#2c3847!important}
[data-testid="stDataFrame"], [data-testid="stTable"]{border:1px solid #2c3847!important;border-radius:10px}
[data-testid="stDataFrame"] button, [data-testid="stDataFrame"] [data-testid="stElementToolbar"],
[data-testid="stDataFrame"] [data-testid="stElementToolbar"] button,
[data-testid="stDataFrame"] [data-testid="stDataFrameToolbar"],
[data-testid="stDataFrame"] [role="button"] {background-color:#1b2938!important;color:#e6edf5!important}
[data-testid="stDialog"] [role="dialog"], [data-testid="stDialog"] [data-testid="stVerticalBlock"],
[data-testid="stDialog"] [data-testid="stDialogContainer"] {background-color:#101a26!important;color:#e6edf5!important}
/* Checkboxes and radio labels and secondary Streamlit menus stay readable. */
[data-testid="stRadio"] label *, [data-testid="stCheckbox"] label *,
[data-testid="stNumberInput"] label *, [data-testid="stSlider"] label *,
[data-testid="stExpander"] summary *,
[data-testid="stSelectbox"] [role="combobox"] * {color:#e6edf5!important;-webkit-text-fill-color:#e6edf5!important}
[data-baseweb="popover"], [data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [role="option"] {background-color:#172231!important;color:#e6edf5!important}
[data-baseweb="popover"] [role="option"]:hover {background-color:#30465d!important}
.rsm-bubble,.rsm-etfbubble{cursor:pointer}

div[data-testid="stExpander"]{background:#101824;border:1px solid #253142;border-radius:10px}
[data-testid="stAlert"]{border-radius:10px}
.block-container hr{border-color:#233142}
.rsm-brand{display:flex;align-items:center;gap:14px;margin:4px 0 12px}
.rsm-brandmark{width:35px;height:35px;display:grid;place-items:center;background:#18293b;border:1px solid #2d5771;border-radius:8px;color:#54b9e9;font-weight:900;font-size:19px}
.rsm-title{font-size:24px;font-weight:820;letter-spacing:1px;line-height:1.05;color:#f4f8ff}
.rsm-subtitle{font-size:12px;color:#94a7bd;margin-top:4px}
.rsm-chip{font-size:11px;letter-spacing:.5px;background:#173528;color:#64df9b;padding:5px 9px;border-radius:7px;border:1px solid #22543b}
.rsm-note{font-size:12px;color:#8295a9}
.rsm-head{font-size:12px;color:#7f95ae;font-weight:750;letter-spacing:1.1px;margin:0 0 10px;text-transform:uppercase}
.rsm-rail{background:#101822;border:1px solid #293648;border-radius:12px;padding:15px 14px}
.rsm-sector{display:flex;align-items:center;gap:7px;padding:8px 1px;border-bottom:1px solid #1b2939}
.rsm-sector:last-child{border-bottom:0}
.rsm-rank{font-size:10px;color:#6e8298;width:17px;flex:none}
.rsm-sname{font-size:11px;font-weight:650;color:#dae4ee;width:125px;flex:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rsm-track{height:7px;background:#293444;border-radius:6px;flex:1;overflow:hidden;min-width:15px}
.rsm-fill{height:100%;border-radius:6px}
.rsm-rs{font-size:11px;font-weight:750;width:45px;text-align:right;flex:none}
.rsm-matrix{overflow-x:auto;border:1px solid #2a394b;border-radius:12px;background:#111a25}
.rsm-grid{min-width:670px}
.rsm-matrix-head,.rsm-matrix-row{display:grid;grid-template-columns:175px repeat(4,minmax(112px,1fr)) 70px}
.rsm-matrix-head{position:sticky;top:0;z-index:5;background:#1a2634;border-bottom:1px solid #314254}
.rsm-matrix-head>div{padding:13px 7px;text-align:center;font-size:11px;font-weight:750;color:#c8d6e5;border-left:1px solid #2c3c50}
.rsm-matrix-head>div:first-child{text-align:left;border-left:0}
.rsm-matrix-row{border-bottom:1px solid #273446;min-height:62px}
.rsm-matrix-row:nth-child(even){background:#131f2c}
.rsm-matrix-row:last-child{border-bottom:0}
.rsm-industry{padding:14px 9px;font-size:11px;line-height:1.3;color:#afc0d2;display:flex;align-items:center;overflow-wrap:anywhere}
.rsm-cell{display:flex;align-items:center;justify-content:flex-start;align-content:center;gap:5px;flex-wrap:wrap;padding:9px 6px;border-left:1px solid #273648}
.rsm-bubble{display:inline-flex;align-items:center;justify-content:center;flex:none;width:37px;height:37px;border-radius:50%;font-size:9px;font-weight:800;text-decoration:none!important;letter-spacing:-.15px;color:#fff!important;border:1px solid #ffffff22;transition:transform .14s ease,box-shadow .14s ease}
.rsm-bubble:hover{transform:scale(1.14);box-shadow:0 0 0 2px #fff5;z-index:2}
.rsm-empty{color:#3d4c5d;font-size:11px}
.rsm-foot{font-size:11px;color:#7d8fa4;padding:10px 4px}
.rsm-etftable{overflow-x:auto;border:1px solid #2a394b;border-radius:12px;background:#111a25;margin:12px 0}
.rsm-etfinner{min-width:760px}
.rsm-etfrow{display:grid;grid-template-columns:185px minmax(570px,1fr);align-items:center;border-bottom:1px solid #273648;min-height:80px}
.rsm-etfrow:nth-child(even){background:#131f2c}
.rsm-etfrow:last-child{border-bottom:0}
.rsm-etflabel{font-size:12px;color:#dce8f4;padding:12px;border-right:1px solid #293749}
.rsm-etflabel b{color:#f7fbff;font-size:14px}
.rsm-etfchips{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:9px 12px}
.rsm-etfbubble{display:inline-flex;align-items:center;justify-content:center;width:49px;height:49px;border-radius:50%;font-size:10px;font-weight:800;color:#f9fbff!important;border:1px solid #ffffff30;text-decoration:none!important;transition:transform .14s ease;flex:none}
.rsm-etfbubble:hover{transform:scale(1.13);box-shadow:0 0 0 2px #ffffff55}

.rsm-pill{display:inline-block;font-size:11px;color:#c2d0df;border:1px solid #34455a;border-radius:15px;padding:4px 10px;margin-right:8px;margin-top:3px}
.rsm-section{font-size:17px;color:#ecf2f8;font-weight:750;margin:12px 0 4px}
.rsm-small{font-size:12px;color:#9daec2;margin:2px 0 12px}
@media(max-width:900px){[data-testid="stMainBlockContainer"]{padding-left:1rem!important;padding-right:1rem!important}.rsm-matrix-head,.rsm-matrix-row{grid-template-columns:135px repeat(4,110px) 65px}.rsm-brand{flex-wrap:wrap}.rsm-title{font-size:20px}}

/* v5 contrast: popup is portalled outside Streamlit's widget subtree.
   Dark background AND light foreground must be forced on the same popup nodes. */
html body div[data-baseweb="popover"],
html body div[data-baseweb="popover"] > div,
html body div[data-baseweb="popover"] > div > div,
html body div[data-baseweb="popover"] [data-baseweb="menu"],
html body div[data-baseweb="popover"] [data-baseweb="menu"] > div,
html body ul[role="listbox"],
html body div[role="listbox"],
html body div[data-baseweb="menu"],
html body [data-testid="stSelectboxVirtualDropdown"],
html body [data-testid="stSelectboxVirtualDropdown"] > div {
  background:#172231!important;background-color:#172231!important;
  color:#e6edf5!important;color-scheme:dark!important;
  border-color:#40536a!important;
}
html body div[data-baseweb="popover"] [role="option"],
html body div[data-baseweb="popover"] [role="option"] *,
html body [data-baseweb="menu"] [role="option"],
html body [data-baseweb="menu"] [role="option"] *,
html body [role="listbox"] [role="option"],
html body [role="listbox"] [role="option"] *,
html body [data-testid="stSelectboxVirtualDropdown"] * {
 color:#e6edf5!important;-webkit-text-fill-color:#e6edf5!important;opacity:1!important;
}
html body div[data-baseweb="popover"] [role="option"][aria-selected="true"],
html body [role="listbox"] [role="option"]:hover,
html body [data-baseweb="menu"] [role="option"]:hover {
 background:#30455c!important;
}
html body [data-testid="stSelectbox"] [data-baseweb="select"] *,
html body [data-testid="stMultiSelect"] [data-baseweb="select"] *,
html body [data-testid="stSelectbox"] [role="combobox"] *,
html body [data-testid="stSelectbox"] [role="combobox"],
html body [data-testid="stMultiSelect"] [role="combobox"] {
 color:#e6edf5!important;-webkit-text-fill-color:#e6edf5!important;
}

/* Force dark backgrounds also on each unselected row. Otherwise a browser
   may render white option rows with our white text. */
html body [data-baseweb="popover"] [role="option"],
html body [data-baseweb="menu"] [role="option"],
html body [role="listbox"] [role="option"],
html body div[data-baseweb="popover"] li,
html body [data-testid="stSelectboxVirtualDropdown"] [role="option"] {
 background-color:#172231!important;color:#e6edf5!important;
 -webkit-text-fill-color:#e6edf5!important;
}
html body [data-baseweb="popover"] [role="option"]:hover,
html body [data-baseweb="popover"] [role="option"][aria-selected="true"],
html body [role="listbox"] [role="option"]:hover,
html body [role="listbox"] [role="option"][aria-selected="true"] {
 background-color:#314963!important;
}
/* Sector / industry grouped matrix with no Unknown column */
.rsm-matrix{overflow-x:auto}
.rsm-grid{min-width:850px}
.rsm-matrix-head{display:grid;grid-template-columns:75px 235px repeat(4,minmax(128px,1fr))}
.rsm-matrix-head>div{font-size:13px;letter-spacing:.2px;padding:14px 9px}
.rsm-sector-group{display:grid;grid-template-columns:75px minmax(0,1fr);border-bottom:2px solid #3b5266}
.rsm-sector-band{display:flex;align-items:center;justify-content:center;gap:12px;flex-direction:column;background:#1a2a3a;border-right:1px solid #456077;min-height:80px;padding:15px 0}
.rsm-sector-vertical{writing-mode:vertical-rl;transform:rotate(180deg);font-weight:800;font-size:14px;letter-spacing:.65px;color:#d9e8f7;text-align:center;max-height:440px}
.rsm-sector-count{font-size:12px;color:#a8c1d8}
.rsm-sector-rows{min-width:0}
.rsm-matrix-row{display:grid;grid-template-columns:235px repeat(4,minmax(128px,1fr));min-height:66px}
.rsm-industry{padding:14px 12px;font-size:14px;font-weight:600;line-height:1.4;color:#d3e0ec}
.rsm-cell{padding:8px;gap:6px}
.rsm-bubble{width:41px;height:41px;font-size:10px}
.rsm-sname{font-size:13px;width:150px}
.rsm-rank{font-size:12px;width:22px}
.rsm-rs{font-size:12px;width:49px}
.rsm-sector{padding:10px 0}
.rsm-etflabel{font-size:14px}
.rsm-etflabel b{font-size:15px}
/* SPDR: never hide the names in the left margin of the chart. */
.rsm-spdr-ranks{border:1px solid #2b3c4d;border-radius:12px;padding:12px 16px;background:#131b26}
.rsm-spdr-rank{display:grid;grid-template-columns:minmax(205px,240px) minmax(120px,1fr) 72px;gap:12px;align-items:center;min-height:41px;border-bottom:1px solid #253142}
.rsm-spdr-rank:last-child{border:0}
.rsm-spdr-name{font-size:13px;color:#e1ebf5;white-space:normal;line-height:1.3}
.rsm-spdr-name b{color:#f5f9fd;margin-right:7px}
.rsm-spdr-track{background:#253142;border-radius:6px;height:13px;position:relative;overflow:hidden}
.rsm-spdr-track::after{content:'';position:absolute;left:50%;top:0;bottom:0;width:1px;background:#8195a9}
.rsm-spdr-bar{position:absolute;top:0;height:100%;border-radius:4px;min-width:2px}
.rsm-spdr-value{font-size:13px;font-weight:750;text-align:right}
@media(max-width:1100px){
 .rsm-matrix-head{grid-template-columns:65px 195px repeat(4,minmax(115px,1fr))}
 .rsm-sector-group{grid-template-columns:65px minmax(0,1fr)}
 .rsm-matrix-row{grid-template-columns:195px repeat(4,minmax(115px,1fr))}
 .rsm-spdr-rank{grid-template-columns:minmax(150px,190px) minmax(70px,1fr) 60px;gap:7px}
}

/* v7: all ticker-bearing lists use a dark native HTML table. */
.rsm-table-shell{overflow:auto;width:100%;border:1px solid #314154;border-radius:10px;background:#111a26;scrollbar-color:#53677e #142132}
.rsm-list-table{border-collapse:separate;border-spacing:0;width:100%;min-width:760px;color:#e7eef8;font-size:13px}
.rsm-list-table th{position:sticky;top:0;z-index:4;background:#203046;color:#dceafa;text-align:left;font-weight:700;padding:10px 11px;border-bottom:1px solid #405167;white-space:nowrap}
.rsm-list-table td{padding:9px 11px;border-bottom:1px solid #26384a;background:#131e2b;white-space:nowrap;max-width:335px;overflow:hidden;text-overflow:ellipsis}
.rsm-list-table tbody tr:nth-child(2n) td{background:#172331}
.rsm-list-table tbody tr:hover td{background:#253b51}
.rsm-list-table td .rsm-ticker-link,.rsm-spdr-rank .rsm-ticker-link{color:#a9dbff!important;font-weight:800;text-decoration:none;border-bottom:1px dotted #7799b2;cursor:zoom-in}
.rsm-list-table td .rsm-ticker-link:hover,.rsm-spdr-rank .rsm-ticker-link:hover{color:#ffffff!important}
.rsm-list-table .rsm-up{color:#56dfa0}.rsm-list-table .rsm-down{color:#ff868e}
.rsm-bubble,.rsm-etfbubble{cursor:zoom-in!important}
.rsm-watch-hint{color:#afc1d5;font-size:12px;margin:6px 0 12px}

/* v8: sortable HTML headers, dark action buttons and compact popup. */
.rsm-sort-head{display:flex;align-items:center;gap:7px;background:transparent!important;color:#dceafa!important;border:0!important;padding:0!important;cursor:pointer;font:inherit;font-weight:750;text-align:left;white-space:nowrap}
.rsm-sort-head:hover{color:#ffffff!important}
.rsm-sort-head:focus-visible{outline:2px solid #7fcaff!important;outline-offset:4px}
.rsm-sort-arrow{font-size:12px;color:#89abc9!important}
[data-testid="stDialog"] [data-testid="stVerticalBlock"]{gap:.4rem!important}
[data-testid="stDialog"] [data-testid="stElementContainer"]{margin-bottom:0!important}
[data-testid="stDialog"] .stButton button[kind="secondary"],
[data-testid="stDialog"] .stLinkButton a {background:#223247!important;color:#e6edf5!important;border:1px solid #466079!important}
[data-testid="stDialog"] .stButton button[kind="secondary"] *,
[data-testid="stDialog"] .stLinkButton a * {color:#e6edf5!important}
[data-testid="stDialog"] .stButton button[kind="primary"] {color:#08120d!important}
</style>
""", unsafe_allow_html=True)

SPDR = {
    "XLK":"Technology", "XLF":"Financials", "XLE":"Energy", "XLV":"Health Care",
    "XLI":"Industrials", "XLY":"Consumer Discretionary", "XLP":"Consumer Staples",
    "XLU":"Utilities", "XLB":"Materials", "XLRE":"Real Estate", "XLC":"Communication Services",
}
PERIODS = ["1D", "1W", "1M", "3M", "6M", "YTD"]
HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; RSMatrixResearch/3.0)"}
TIER_ORDER = ["Mega", "Large", "Mid", "Small"]

# Hyperlink bubbles use same-app query parameters, not external tabs.
# Streamlit does not expose click callbacks from arbitrary st.markdown HTML,
# so this URL navigation is the supported no-extra-dependency bridge.
WORKSPACES = ["RS MATRIX", "SECTOR SPDR", "SECTOR ROTATION", "MARKET BREADTH",
              "MACRO MARKETS", "MINERVINI SCANNER", "MY WATCHLIST"]
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9^][A-Za-z0-9.^=_-]{0,22}$")

def valid_ticker(value):
    """Return a real symbol, never stringified Python nulls such as 'NONE'."""
    if value is None or not isinstance(value, (str, int)):
        return ""
    ticker=str(value).strip().upper()
    if ticker in {"", "NONE", "NULL", "NAN", "NAT", "<NA>", "UNDEFINED", "FALSE"}:
        return ""
    return ticker if SYMBOL_PATTERN.fullmatch(ticker) else ""

def popup_href(ticker, view_name, rs_window="1W"):
    symbol=valid_ticker(ticker)
    if not symbol:
        return "#"
    return "?"+urlencode({"rsm_chart":symbol, "rsm_view":view_name, "rsm_window":rs_window})

# -------- Shared watchlist: anonymous, editable by anyone with the app URL --------
# Supabase is the durable backend. When it is not configured, SQLite is a
# temporary shared fallback and will be reset by Community Cloud redeploys.
WATCH_DB = Path('/tmp/rsm_shared_watchlist.sqlite3')
WATCH_LOCK = threading.RLock()
WATCH_MAX = 200

def _sb_cfg():
    try:
        url=str(st.secrets.get('SUPABASE_URL','')).strip().rstrip('/')
        key=str(st.secrets.get('SUPABASE_PUBLISHABLE_KEY', st.secrets.get('SUPABASE_ANON_KEY',''))).strip()
        if url.startswith('https://') and key:
            return url,key
    except Exception:
        pass
    return None

def watchlist_durable():
    return _sb_cfg() is not None

def _sb_request(method, query='', body=None, extra_headers=None):
    config=_sb_cfg()
    if not config:
        raise RuntimeError('Persistent watchlist is not configured')
    url,key=config
    headers={'apikey':key,'Accept':'application/json','Content-Type':'application/json'}
    # Legacy anon JWTs use Authorization; new sb_publishable_* keys must not.
    if key.startswith('eyJ'):
        headers['Authorization']='Bearer '+key
    if extra_headers:headers.update(extra_headers)
    response=requests.request(method,url+'/rest/v1/shared_watchlist'+query,
                              headers=headers,json=body,timeout=15)
    if response.status_code not in (200,201,204):
        raise RuntimeError(f'Supabase HTTP {response.status_code}: '+response.text[:140])
    if response.status_code==204 or not response.content:return []
    return response.json()

def _db():
    connection=sqlite3.connect(str(WATCH_DB),timeout=10)
    connection.execute('CREATE TABLE IF NOT EXISTS shared_watchlist (symbol TEXT PRIMARY KEY, added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    connection.commit()
    return connection

def watchlist_symbols():
    if watchlist_durable():
        records=_sb_request('GET','?select=symbol,added_at&order=added_at.desc&limit=250')
        return [valid_ticker(r.get('symbol','')) for r in records if valid_ticker(r.get('symbol',''))]
    with WATCH_LOCK:
        with _db() as connection:
            records=connection.execute('SELECT symbol FROM shared_watchlist ORDER BY added_at DESC,symbol LIMIT 250').fetchall()
        return [r[0] for r in records if valid_ticker(r[0])]

def watchlist_add(ticker):
    symbol=valid_ticker(ticker)
    if not symbol:
        raise ValueError('Invalid ticker format')
    present=watchlist_symbols()
    if symbol in present:
        return False
    if len(present)>=WATCH_MAX:
        raise ValueError(f'Watchlist is limited to {WATCH_MAX} tickers')
    if watchlist_durable():
        _sb_request('POST','?on_conflict=symbol',[{'symbol':symbol}],
                    {'Prefer':'resolution=ignore-duplicates,return=minimal'})
        return True
    with WATCH_LOCK:
        with _db() as connection:
            connection.execute('INSERT OR IGNORE INTO shared_watchlist(symbol) VALUES(?)',(symbol,))
            connection.commit()
    return True

def watchlist_remove(ticker):
    symbol=valid_ticker(ticker)
    if not symbol:raise ValueError('Invalid ticker')
    if watchlist_durable():
        _sb_request('DELETE','?symbol=eq.'+quote(symbol,safe=''),None,{'Prefer':'return=minimal'})
        return
    with WATCH_LOCK:
        with _db() as connection:
            connection.execute('DELETE FROM shared_watchlist WHERE symbol=?',(symbol,))
            connection.commit()

def watchlist_banner():
    if watchlist_durable():
        st.caption('Shared persistent watchlist · all visitors can add or remove tickers · Supabase storage.')
    else:
        st.warning('The shared watchlist currently uses temporary server storage: everyone can see and edit it, '
                   'but it can be cleared by Streamlit restarts or redeploys. For permanent storage, configure '
                   'Supabase in Streamlit app secrets (instructions in README).')

def dark_table(frame, *, key, ticker_col=None, **kwargs):
    """Dark, scrollable HTML table; hover any ticker to open the v6 chart.

    Links and text are HTML-escaped, numeric formatting stays human-readable.
    The downloadable CSV remains the full data set for large scanners.
    """
    if frame is None or frame.empty:
        st.info("No rows available for this table.")
        return
    if ticker_col is None or ticker_col not in frame.columns:
        styled=frame.style.set_properties(**{"background-color":"#131b26","color":"#e6edf5"})
        st.dataframe(styled,key=key,**kwargs)
        return
    height=int(kwargs.get('height',520) or 520)
    height=max(160,min(height,900))
    shown=frame.head(350)
    cols=list(shown.columns)
    rows=[f'<div class="rsm-table-shell" style="max-height:{height}px">',
          '<table class="rsm-list-table"><thead><tr>']
    for i,col in enumerate(cols):
        safe=html.escape(str(col))
        rows.append(f'<th aria-sort="none"><button type="button" class="rsm-sort-head" '
                    f'data-rsm-sortcol="{i}" title="Sort by {safe}" aria-label="Sort by {safe}">'
                    f'{safe}<span class="rsm-sort-arrow" aria-hidden="true">⇅</span></button></th>')
    rows.append('</tr></thead><tbody>')
    for _,rec in shown.iterrows():
        rows.append('<tr>')
        for col in cols:
            val=rec[col]
            if col==ticker_col:
                tick=valid_ticker(val)
                if tick:
                    url=popup_href(tick,view if 'view' in globals() else 'RS MATRIX',
                                   period if 'period' in globals() else '1W')
                    out=(f'<a class="rsm-ticker-link" data-rsm-ticker="{html.escape(tick,quote=True)}" '
                         f'href="{html.escape(url,quote=True)}" title="Hover for full chart · click on touch screens">'
                         +html.escape(tick)+'</a>')
                else:out='—'
            elif col in ('TradingView','Source') and isinstance(val,str) and val.startswith('https://'):
                out='<a href="'+html.escape(val,quote=True)+'" target="_blank" rel="noopener noreferrer" style="color:#90c9ed">Open ↗</a>'
            elif pd.isna(val):out='—'
            elif isinstance(val,(bool,np.bool_)):out='✓' if val else '—'
            elif isinstance(val,(float,np.floating)):
                out=f'{val:+.2f}' if col.startswith(('RS','Δ')) or 'change' in col.lower() else f'{val:,.2f}'
                color_class=' rsm-up' if val>0 else ' rsm-down' if val<0 else ''
                out=f'<span class="{color_class}">{html.escape(out)}</span>'
            elif isinstance(val,(int,np.integer)):out=f'{val:,}'
            else:out=html.escape(str(val))
            rows.append('<td>'+out+'</td>')
        rows.append('</tr>')
    rows.append('</tbody></table></div>')
    st.markdown(''.join(rows),unsafe_allow_html=True)
    if len(frame)>len(shown):
        st.caption(f"Displaying first {len(shown):,} of {len(frame):,} rows; export the full CSV if needed.")
    st.caption("Click any table column heading to sort · Hover on a ticker to preview its chart · Click a ticker on touch devices.")


@st.cache_data(ttl=900, show_spinner=False)
def popup_history(ticker):
    """Fetch only the clicked symbol + SPY. Does not re-scan 500 stocks."""
    symbols=[ticker] if ticker=="SPY" else [ticker,"SPY"]
    raw=yf.download(symbols,period="2y",interval="1d",auto_adjust=True,
                    progress=False,threads=True,group_by="column")
    if raw is None or raw.empty:
        return pd.DataFrame(),pd.Series(dtype=float)
    if isinstance(raw.columns,pd.MultiIndex):
        try:
            security=raw.xs(ticker,axis=1,level=-1).copy()
        except (KeyError,ValueError):
            return pd.DataFrame(),pd.Series(dtype=float)
        try:
            spy=raw.xs("SPY",axis=1,level=-1)["Close"].copy()
        except (KeyError,ValueError):
            spy=security["Close"].copy() if ticker=="SPY" else pd.Series(dtype=float)
    else:
        security=raw.copy()
        spy=security["Close"].copy() if ticker=="SPY" and "Close" in security else pd.Series(dtype=float)
    for col in ("Open","High","Low","Close","Volume"):
        if col not in security.columns:
            security[col]=np.nan
    security=security[["Open","High","Low","Close","Volume"]].dropna(subset=["Close"]).sort_index()
    return security,spy.sort_index()

def ohlc_chart(ticker, bars, spy, timeframe, interval):
    work=bars.copy().sort_index()
    reference=spy.copy().sort_index()
    if interval=="Weekly":
        work=work.resample("W-FRI").agg({"Open":"first","High":"max",
            "Low":"min","Close":"last","Volume":"sum"}).dropna(subset=["Close"])
        reference=reference.resample("W-FRI").last() if not reference.empty else reference
    work["MA20"]=work["Close"].rolling(20,min_periods=5).mean()
    work["MA50"]=work["Close"].rolling(50,min_periods=10).mean()
    windows={"1M":31,"3M":93,"6M":186,"1Y":366,"2Y":745}
    start=work.index.max()-pd.Timedelta(days=windows[timeframe])
    shown=work.loc[work.index>=start]
    if len(shown)<2:
        shown=work.tail(40)
    # The displayed RS line is normalized at the first visible bar (100).
    ratio=shown["Close"].div(reference.reindex(shown.index).ffill()) if not reference.empty else pd.Series(dtype=float)
    rs=ratio.div(ratio.dropna().iloc[0]).mul(100) if not ratio.dropna().empty and ratio.dropna().iloc[0]!=0 else pd.Series(dtype=float)
    fig=make_subplots(rows=3,cols=1,shared_xaxes=True,vertical_spacing=.035,
                      row_heights=[.57,.17,.26],subplot_titles=("Price / moving averages","Volume", "RS line vs SPY · base 100"))
    if shown[["Open","High","Low"]].notna().all().all():
        fig.add_trace(go.Candlestick(x=shown.index,open=shown.Open,high=shown.High,low=shown.Low,close=shown.Close,
            increasing_line_color="#24bd76",decreasing_line_color="#f05256",name=ticker),row=1,col=1)
    else:
        fig.add_trace(go.Scatter(x=shown.index,y=shown.Close,mode="lines",name=ticker,
                                 line=dict(color="#24bd76",width=2)),row=1,col=1)
    fig.add_trace(go.Scatter(x=shown.index,y=shown.MA20,name="MA20",mode="lines",
        line=dict(color="#e6b85c",width=1.4)),row=1,col=1)
    fig.add_trace(go.Scatter(x=shown.index,y=shown.MA50,name="MA50",mode="lines",
        line=dict(color="#5cacf0",width=1.4)),row=1,col=1)
    colors=np.where(shown.Close>=shown.Open,"#24bd76","#f05256")
    fig.add_trace(go.Bar(x=shown.index,y=shown.Volume,marker_color=colors,showlegend=False,name="Volume"),row=2,col=1)
    if not rs.empty:
        rs_shown=rs.reindex(shown.index).dropna()
        if not rs_shown.empty:
            fig.add_trace(go.Scatter(x=rs_shown.index,y=rs_shown,mode="lines",
                line=dict(color="#d5a5ff",width=2),name="RS/SPY"),row=3,col=1)
            fig.add_hline(y=100,line_color="#6b829a",line_dash="dot",row=3,col=1)
    fig.update_layout(height=420,margin=dict(l=22,r=18,t=33,b=8),
       paper_bgcolor="#101a26",plot_bgcolor="#101a26",font=dict(color="#e6edf5",size=10),
       hovermode="x unified",legend=dict(orientation="h",y=1.07,x=0),
       xaxis_rangeslider_visible=False,
       modebar_bgcolor="#1b2938",modebar_color="#dce8f5")
    fig.update_xaxes(showgrid=True,gridcolor="#2b3a4b",rangeslider_visible=False)
    fig.update_yaxes(showgrid=True,gridcolor="#2b3a4b",zeroline=False)
    return fig

@st.dialog("Chart preview · shared watchlist",width="large")
def show_ticker_popup(ticker):
    ticker=valid_ticker(ticker)
    if not ticker:
        # Never expose an unusable watchlist button for a missing symbol.
        st.warning("No valid ticker was selected. Hover or click on a specific stock or ETF symbol.")
        return

    # Watchlist control is deliberately ABOVE the price chart so it is visible
    # without scrolling, and its label always identifies the selected symbol.
    heading,action=st.columns([1.7,1.2],vertical_alignment="center")
    with heading:
        st.markdown(f"### {html.escape(ticker)} · Price / RS chart")
        st.caption("Shared watchlist — visible to everyone using this public app")
    with action:
        try:
            already_saved=ticker in watchlist_symbols()
            if already_saved:
                if st.button(f"✓ {ticker} saved · Remove",key="popup_remove_"+ticker,use_container_width=True):
                    watchlist_remove(ticker)
                    st.rerun(scope="fragment")
            else:
                if st.button(f"＋ Add {ticker} to Watchlist",key="popup_add_"+ticker,
                             type="primary",use_container_width=True):
                    watchlist_add(ticker)
                    st.rerun(scope="fragment")
        except Exception as exc:
            st.error("Shared watchlist is unavailable: "+str(exc)[:140])

    tf,iv=st.columns([1,1],gap="small")
    with tf:
        window=st.selectbox("History",["1M","3M","6M","1Y","2Y"],index=2,key="pop_tf_"+ticker)
    with iv:
        interval=st.radio("Bars",["Daily","Weekly"],horizontal=True,key="pop_bars_"+ticker)
    try:
        if ticker in FRED_RATES:
            rates=fred_rates()
            if rates.empty or ticker not in rates or rates[ticker].dropna().empty:
                st.warning(f"No available observations for {ticker}.")
            else:
                vals=rates[ticker].dropna()
                days={"1M":31,"3M":93,"6M":186,"1Y":366,"2Y":745}[window]
                vals=vals[vals.index>=vals.index.max()-pd.Timedelta(days=days)]
                fig=go.Figure(go.Scatter(x=vals.index,y=vals.values,mode="lines+markers",
                    line=dict(color="#48c89b",width=2),marker=dict(size=3),name="Rate %"))
                fig.update_layout(height=335,paper_bgcolor="#101a26",plot_bgcolor="#101a26",
                    font=dict(color="#e6edf5"),margin=dict(l=15,r=15,t=12,b=10),
                    xaxis=dict(gridcolor="#2b3a4b"),yaxis=dict(title="Rate / Yield (%)",gridcolor="#2b3a4b"))
                st.plotly_chart(fig,use_container_width=True,theme=None,key="popup_fred_"+ticker)
                st.caption("FRED observation, not a real-time quote · "+str(pd.Timestamp(vals.index[-1]).date()))
        else:
            with st.spinner(f"Loading {ticker} price history…"):
                bars,reference=popup_history(ticker)
            if bars.empty:
                st.warning(f"No price bars returned for {ticker}. You may still save this ticker to the shared watchlist above.")
            else:
                fig=ohlc_chart(ticker,bars,reference,window,interval)
                st.plotly_chart(fig,use_container_width=True,theme=None,key="popup_fig_"+ticker)
                st.caption(f"{ticker} · {pd.Timestamp(bars.index[-1]).date()} close · indicative/delayed Yahoo daily data · RS/SPY = ratio normalized to 100")
    except Exception as exc:
        st.warning(f"Could not load {ticker}: "+str(exc)[:150])

    left,right=st.columns(2,gap="small")
    with left:
        if ticker in FRED_RATES:
            st.link_button(f"{ticker} · FRED source ↗", "https://fred.stlouisfed.org/series/"+quote(ticker,safe=""),use_container_width=True)
        else:
            st.link_button(f"{ticker} · TradingView ↗",
                "https://www.tradingview.com/chart/?symbol="+quote(ticker,safe=""),use_container_width=True)
    with right:
        if st.button("Close chart",use_container_width=True,key="close_popup_"+ticker):
            st.rerun()


def fmt_signed(x):
    return f"{x:+.2f}%" if pd.notna(x) else "—"


def color_rs(x):
    if pd.isna(x): return "#415164"
    # Saturated enough to remain legible in a crowded trading matrix.
    if x >= 8: return "#0d8e56"
    if x >= 3: return "#168c61"
    if x >= 1: return "#3d996b"
    if x >= 0: return "#698b70"
    if x >= -1: return "#8b635e"
    if x >= -3: return "#b64b4b"
    return "#ce343b"


def cap_tier(value):
    if pd.isna(value) or value <= 0: return "Unknown"
    if value >= 200e9: return "Mega"
    if value >= 50e9: return "Large"
    if value >= 20e9: return "Mid"
    return "Small"


@st.cache_data(ttl=12*3600, show_spinner=False)
def get_snapshot():
    """Nasdaq-sourced market caps and listings, publisher updates on weekdays.
    This is NOT a live market-cap feed and is not an official GICS sector source.
    """
    url = "https://raw.githubusercontent.com/zyhe16/top-us-stock-tickers/main/data/v2/tickers.csv"
    r = requests.get(url, headers=HEADERS, timeout=22)
    r.raise_for_status()
    snap = pd.read_csv(io.StringIO(r.text), keep_default_na=False, low_memory=False)
    needed = {"symbol","name","market_cap","sector","industry","is_sp500"}
    if not needed.issubset(snap.columns) or len(snap) < 3000:
        raise RuntimeError("Nasdaq snapshot incomplete")
    snap["Symbol"] = snap["symbol"].astype(str).str.upper().str.replace("/", "-", regex=False).str.replace(".", "-",regex=False)
    snap["Market Cap"] = pd.to_numeric(snap["market_cap"], errors="coerce")
    snap["Market Cap"] = snap["Market Cap"].where(snap["Market Cap"] > 0)
    snap["Sector Source"] = snap["sector"].replace("", "Unclassified")
    snap["Industry Source"] = snap["industry"].replace("", "Unclassified")
    snap = snap.drop_duplicates("Symbol")
    return snap


@st.cache_data(ttl=86400, show_spinner=False)
def get_sp500():
    errors=[]
    for url in (
        "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    ):
        try:
            r = requests.get(url,headers=HEADERS,timeout=20)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text),dtype=str) if "csv" in url else pd.read_html(io.StringIO(r.text))[0]
            df = df.rename(columns={"GICS Sector":"Sector","GICS Sub-Industry":"Industry","Name":"Security"})
            df["Symbol"] = df["Symbol"].astype(str).str.replace(".","-",regex=False)
            df["Industry"] = df.get("Industry",pd.Series("Unclassified",index=df.index)).fillna("Unclassified")
            df = df[["Symbol","Security","Sector","Industry"]].drop_duplicates("Symbol").dropna(subset=["Symbol"])
            if len(df)>400: return df
            errors.append("short S&P 500 list")
        except Exception as exc:
            errors.append(str(exc)[:100])
    # If both canonical sources fail, use snapshot-flagged S&P membership; mark classification source.
    try:
        snap=get_snapshot()
        flags=snap["is_sp500"].astype(str).str.lower().eq("true")
        subset=snap.loc[flags].copy()
        if len(subset) > 400:
            subset=subset.rename(columns={"name":"Security","Sector Source":"Sector","Industry Source":"Industry"})
            return subset[["Symbol","Security","Sector","Industry"]]
    except Exception as exc:
        errors.append(str(exc)[:100])
    raise RuntimeError("S&P 500 constituents unavailable: " + "; ".join(errors))


@st.cache_data(ttl=86400, show_spinner=False)
def fallback_all_us():
    """Fallback if GitHub Nasdaq snapshot unavailable; cannot provide reliable cap tiers."""
    def txt(url):
        r=requests.get(url,headers=HEADERS,timeout=20);r.raise_for_status()
        return pd.read_csv(io.StringIO(r.text),sep="|",dtype=str)
    nas=txt("https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt")
    nas=nas[(nas["Test Issue"]=="N") & nas["Symbol"].notna()]
    nas=nas[["Symbol","Security Name"]].rename(columns={"Security Name":"Security"})
    other=txt("https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt")
    other=other[(other["Test Issue"]=="N") & other["Exchange"].isin(["N","A"])]
    other=other[["ACT Symbol","Security Name"]].rename(columns={"ACT Symbol":"Symbol","Security Name":"Security"})
    out=pd.concat([nas,other],ignore_index=True).drop_duplicates("Symbol")
    out["Symbol"]=out["Symbol"].str.replace(".","-",regex=False)
    out=out[out.Symbol.str.fullmatch(r"[A-Z]{1,5}(-[A-Z])?",na=False)]
    out=out[~out.Security.str.contains(r"ETF|ETN|Warrant|Preferred|Depositary|Units|Rights",case=False,regex=True,na=False)]
    out["Market Cap"]=np.nan
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def prices(symbols):
    """Batch daily adjusted history. Caller must not assume exact synchronicity."""
    symbols=list(dict.fromkeys(["SPY"]+list(symbols)))
    closes=[];volumes=[]
    for i in range(0,len(symbols),70):
        batch=symbols[i:i+70]
        try:
            raw=yf.download(batch, period="18mo", interval="1d", auto_adjust=True,
                            progress=False, threads=True, group_by="column")
            if raw.empty: continue
            if isinstance(raw.columns,pd.MultiIndex):
                c=raw["Close"]; v=raw["Volume"]
            else:
                c=raw[["Close"]].rename(columns={"Close":batch[0]})
                v=raw[["Volume"]].rename(columns={"Volume":batch[0]})
            if isinstance(c,pd.Series): c=c.to_frame(name=batch[0])
            if isinstance(v,pd.Series): v=v.to_frame(name=batch[0])
            closes.append(c);volumes.append(v)
        except Exception:
            continue
    if not closes: return pd.DataFrame(),pd.DataFrame()
    c=pd.concat(closes,axis=1).loc[:,lambda x: ~x.columns.duplicated()]
    v=pd.concat(volumes,axis=1).loc[:,lambda x: ~x.columns.duplicated()]
    return c.sort_index(),v.reindex(c.index)


def lookback_for(period, index):
    if period!="YTD":return {"1D":1,"1W":5,"1M":21,"3M":63,"6M":126}[period]
    if len(index)==0:return 1
    last=pd.Timestamp(index[-1]).tz_localize(None) if pd.Timestamp(index[-1]).tzinfo else pd.Timestamp(index[-1])
    in_year=sum(pd.Timestamp(d).year==last.year for d in index)
    return max(1,in_year-1)


def period_rs(close, days, offset=0):
    if close.empty or "SPY" not in close:return pd.Series(dtype=float)
    c=close.ffill(limit=3)
    if len(c)<=days+offset:return pd.Series(dtype=float)
    end = c.iloc[len(c)-1-offset]
    start=c.iloc[len(c)-1-offset-days]
    spy_ratio=end.get("SPY",np.nan)/start.get("SPY",np.nan)
    if not np.isfinite(spy_ratio) or spy_ratio<=0:return pd.Series(dtype=float)
    return ((end/start)/spy_ratio-1)*100


def build_signals(close, volume, days, universe):
    close=close.ffill(limit=3)
    if close.empty or "SPY" not in close or len(close)<205:return pd.DataFrame()
    rs=period_rs(close,days)
    rs_week=period_rs(close,5)
    rs_prev=period_rs(close,5,offset=5)
    rs_1m=period_rs(close,21)
    last=close.iloc[-1]
    ma50=close.rolling(50,min_periods=50).mean().iloc[-1]
    ma200=close.rolling(200,min_periods=200).mean().iloc[-1]
    # Last observed volumes may reflect an incomplete trading day; view is labelled accordingly.
    vol=volume.reindex(index=close.index,columns=close.columns).fillna(0)
    prior_avg=vol.shift(1).rolling(20,min_periods=15).mean().iloc[-1].replace(0,np.nan)
    rvol=vol.iloc[-1]/prior_avg
    up=close.diff().tail(50)>0; down=close.diff().tail(50)<0
    upvol=vol.tail(50).where(up).sum()
    dnvol=vol.tail(50).where(down).sum()
    ud=upvol/dnvol.replace(0,np.nan)
    line=close.div(close["SPY"],axis=0)
    prior20=line.shift(1).rolling(20,min_periods=20).max().iloc[-1]
    line_break=(line.iloc[-1]>prior20) & (line.shift(1).iloc[-1]<=prior20)
    signal=pd.DataFrame({
        "Symbol":rs.index, "RS %":rs.values,
        "RS 1W %":rs_week.reindex(rs.index).values,
        "RS 1M %":rs_1m.reindex(rs.index).values,
        "RS acceleration":(rs_week-rs_prev).reindex(rs.index).values,
        "RS new 20D high":line_break.reindex(rs.index).fillna(False).values,
        "Price":last.reindex(rs.index).values,
        "MA50":ma50.reindex(rs.index).values,
        "MA200":ma200.reindex(rs.index).values,
        "RVOL":rvol.reindex(rs.index).values,
        "U/D proxy":ud.reindex(rs.index).values,
    })
    signal=signal[signal.Symbol!="SPY"].dropna(subset=["RS %","Price"])
    signal=signal.merge(universe,on="Symbol",how="left")
    signal["Sector"]=signal["Sector"].fillna("Unclassified")
    signal["Industry"]=signal["Industry"].fillna("Unclassified")
    signal["Market Cap"]=pd.to_numeric(signal["Market Cap"],errors="coerce")
    signal["Cap tier"]=signal["Market Cap"].map(cap_tier)
    signal["Trend"]=(signal.Price>signal.MA50)&(signal.MA50>signal.MA200)
    signal["Minervini candidate"]=(signal["RS 1W %"]>0)&(signal["RS 1M %"]>0)&signal.Trend&(signal.RVOL>1)&(signal["U/D proxy"]>1.5)
    return signal


@st.cache_data(ttl=21600, show_spinner=False)
def spdr_holdings(etf):
    """Top 10 reported provider positions; no invented/stale hardcoded holdings."""
    try:
        f=yf.Ticker(etf).funds_data.top_holdings
        if isinstance(f,pd.DataFrame) and not f.empty:
            if "Symbol" not in f.columns: f=f.reset_index().rename(columns={"index":"Symbol"})
            sc=next((c for c in f if str(c).lower() in ("symbol","ticker","holding")),None)
            wc=next((c for c in f if "weight" in str(c).lower() or "holding percent" in str(c).lower()),None)
            if sc and wc:
                out=f[[sc,wc]].copy();out.columns=["Symbol","Weight %"]
                out["Weight %"]=pd.to_numeric(out["Weight %"],errors="coerce")
                if out["Weight %"].max()<=1:out["Weight %"]*=100
                out["Symbol"]=out["Symbol"].astype(str).str.replace(".","-",regex=False)
                out=out.dropna().sort_values("Weight %",ascending=False).head(10)
                if len(out)>=5:return out,"Yahoo Finance · holdings date not verified"
    except Exception:
        pass
    try:
        u=f"https://stockanalysis.com/etf/{etf.lower()}/holdings/"
        r=requests.get(u,headers=HEADERS,timeout=12);r.raise_for_status()
        for h in pd.read_html(io.StringIO(r.text)):
            sc=next((c for c in h if str(c).lower().strip() in ("symbol","ticker")),None)
            wc=next((c for c in h if "weight" in str(c).lower()),None)
            if sc and wc:
                out=h[[sc,wc]].copy();out.columns=["Symbol","Weight %"]
                out["Weight %"]=pd.to_numeric(out["Weight %"].astype(str).str.replace("%","",regex=False),errors="coerce")
                out["Symbol"]=out["Symbol"].astype(str).str.replace(".","-",regex=False)
                out=out.dropna().sort_values("Weight %",ascending=False).head(10)
                if len(out)>=5:return out,f"Stock Analysis · {u} · verify date"
    except Exception:
        pass
    return pd.DataFrame(columns=["Symbol","Weight %"]),"Holdings source unavailable"


def sector_rail(frame):
    if frame.empty:return "<div class='rsm-rail'>No sector data</div>"
    groups=frame.groupby("Sector",dropna=False).agg(RS=("RS %","mean"),Count=("Symbol","count")).reset_index()
    groups=groups.sort_values("RS",ascending=False)
    scale=max(groups["RS"].abs().max(),1)
    lines=[]
    for j, row in enumerate(groups.itertuples(index=False)):
        s=html.escape(str(row.Sector)); v=float(row.RS)
        color=color_rs(v);pct=max(5,int(abs(v)/scale*100))
        lines.append(f"<div class='rsm-sector' title='{row.Count} active symbols'>"
                     f"<span class='rsm-rank'>{j+1:02d}</span><span class='rsm-sname'>{s}</span>"
                     f"<div class='rsm-track'><div class='rsm-fill' style='width:{pct}%;background:{color}'></div></div>"
                     f"<span class='rsm-rs' style='color:{color}'>{v:+.1f}</span></div>")
    return "<div class='rsm-rail'><div class='rsm-head'>Sector RS · equal-weight mean</div>"+"".join(lines)+"</div>"


def bubbles_matrix(frame, max_symbols=160, group_col="Industry", rs_window="1W"):
    """Sector group bands run vertically before the industry column.

    Securities without verified cap are omitted rather than put in Unknown;
    their number is reported explicitly in the user interface.
    """
    if frame.empty:
        return "<div class='rsm-rail'>No matching tickers.</div>"
    eligible = frame.loc[frame["Cap tier"].isin(TIER_ORDER)].copy()
    if eligible.empty:
        return "<div class='rsm-rail'>No securities with a known market-cap tier. Check the Nasdaq snapshot source.</div>"
    eligible = eligible.sort_values("RS %",ascending=False).head(max_symbols)
    sector_strength = eligible.groupby("Sector",dropna=False)["RS %"].mean().sort_values(ascending=False)
    lines = ["<div class='rsm-matrix'><div class='rsm-grid'>",
             "<div class='rsm-matrix-head'><div>SECTOR</div><div>INDUSTRY</div>",
             "<div>MEGA <small>≥$200B</small></div><div>LARGE <small>$50–200B</small></div>",
             "<div>MID <small>$20–50B</small></div><div>SMALL <small>&lt;$20B</small></div></div>"]
    for sec in sector_strength.index:
        sector_frame = eligible[eligible["Sector"]==sec]
        ind_strength = (sector_frame.groupby(group_col,dropna=False)["RS %"]
                        .mean().sort_values(ascending=False))
        sec_label=html.escape(str(sec))
        lines.append("<div class='rsm-sector-group'>" +
                     f"<div class='rsm-sector-band'><span class='rsm-sector-vertical'>{sec_label}</span>"+
                     f"<span class='rsm-sector-count'>{len(sector_frame)}</span></div>" +
                     "<div class='rsm-sector-rows'>")
        for ind in ind_strength.index:
            sub=sector_frame.loc[sector_frame[group_col]==ind]
            lines.append("<div class='rsm-matrix-row'><div class='rsm-industry'>"+
                         html.escape(str(ind))+" <span style='color:#8196ab'>&nbsp;· "+str(len(sub))+"</span></div>")
            for tier in TIER_ORDER:
                matching=sub[sub["Cap tier"]==tier]
                circles=[]
                for _,r in matching.iterrows():
                    symbol=str(r["Symbol"])
                    cap=r["Market Cap"]
                    cap_text=f"${cap/1e9:,.1f}B" if pd.notna(cap) else "N/A"
                    tooltip=html.escape(f"{symbol} · {sec} · {ind} · RS {fmt_signed(r['RS %'])} · cap {cap_text}",quote=True)
                    url=popup_href(symbol,"RS MATRIX",rs_window)
                    circles.append(f"<a class='rsm-bubble' data-rsm-ticker='{html.escape(symbol,quote=True)}' target='_self' href='{html.escape(url,quote=True)}' title='{tooltip} · Click for popup chart' style='background:{color_rs(r['RS %'])}'>{html.escape(symbol)}</a>")
                lines.append("<div class='rsm-cell'>"+("".join(circles) if circles else "<span class='rsm-empty'>·</span>")+"</div>")
            lines.append("</div>")
        lines.append("</div></div>")
    lines.append("</div></div>")
    return "".join(lines)


def spdr_rank_html(ranking):
    """Accessible, always-visible labels for all 11 Select Sector SPDR ETFs."""
    if ranking.empty:
        return "<div class='rsm-rail'>No available sector prices.</div>"
    max_abs=max(1.0,ranking["RS vs SPY %"].abs().max(skipna=True))
    lines=["<div class='rsm-spdr-ranks'>"]
    for _,r in ranking.iterrows():
        v=r["RS vs SPY %"]
        val=fmt_signed(v)
        width=0 if pd.isna(v) else min(49.9,abs(float(v))/max_abs*49.9)
        left=(50 if pd.isna(v) or v>=0 else 50-width)
        bgcolor=color_rs(v)
        lines.append("<div class='rsm-spdr-rank'>"
                     f"<div class='rsm-spdr-name'><b><a class='rsm-ticker-link' data-rsm-ticker='{html.escape(str(r['ETF']),quote=True)}' href='{html.escape(popup_href(r['ETF'],'SECTOR SPDR'),quote=True)}'>{html.escape(str(r['ETF']))}</a></b>{html.escape(str(r['Sector']))}</div>"
                     f"<div class='rsm-spdr-track' role='img' aria-label='{html.escape(str(r['ETF'])+' '+val,quote=True)}'>"
                     f"<span class='rsm-spdr-bar' style='left:{left:.2f}%;width:{width:.2f}%;background:{bgcolor}'></span></div>"
                     f"<div class='rsm-spdr-value' style='color:{bgcolor}'>{val}</div></div>")
    return "".join(lines)+"</div>"


def spdr_bubbles(holdings, value_col="RS vs SPY %", rs_window="1W"):
    """Provider-weight sorted, ticker-linked dark bubble rows for SPDR holdings.

    Missing quotes / weights are shown as unavailable and never colored as signal.
    """
    if holdings.empty:
        return "<div class='rsm-rail'>No holdings available.</div>"
    lines=["<div class='rsm-etftable'><div class='rsm-etfinner'>"]
    for etf, group in holdings.groupby("ETF",sort=False):
        sec=html.escape(SPDR.get(etf,etf))
        lines.append(f"<div class='rsm-etfrow'><div class='rsm-etflabel'><b>{html.escape(etf)}</b><div>{sec}</div><div style='font-size:10px;color:#869db2'>Top {len(group)} by ETF weight</div></div><div class='rsm-etfchips'>")
        for _,r in group.sort_values("Weight %",ascending=False).iterrows():
            sym=str(r["Symbol"])
            val=r.get(value_col,np.nan)
            val_str=fmt_signed(val)
            weight=r.get("Weight %",np.nan)
            title=html.escape(f"{sym} · fund weight {weight:.2f}% · {value_col}: {val_str}" if pd.notna(weight) else f"{sym} · {value_col}: {val_str}",quote=True)
            bubble_color=color_rs(val)
            url=popup_href(sym,"SECTOR SPDR",rs_window)
            lines.append(f"<a class='rsm-etfbubble' data-rsm-ticker='{html.escape(sym,quote=True)}' target='_self' style='background:{bubble_color}' href='{html.escape(url,quote=True)}' title='{title} · Click for popup chart'>{html.escape(sym)}</a>")
        lines.append("</div></div>")
    return "".join(lines)+"</div></div>"


def market_scope(sp, snap, use_sp):
    if snap is None:
        if use_sp: df=sp.copy();df["Market Cap"]=np.nan;return df
        try:
            all_us=fallback_all_us()
            joined=all_us.merge(sp[["Symbol","Sector","Industry"]],on="Symbol",how="left")
            joined["Industry"]=joined.Industry.fillna("Unclassified")
            joined["Sector"]=joined.Sector.fillna("Unclassified")
            return joined
        except Exception as exc:
            st.warning("NYSE/Nasdaq list currently unavailable; showing S&P 500 instead. " + str(exc)[:140])
            df=sp.copy();df["Market Cap"]=np.nan;return df
    cols=["Symbol","Market Cap","Sector Source","Industry Source","name"]
    if use_sp:
        out=sp.merge(snap[cols],on="Symbol",how="left")
        return out
    out=snap.copy()
    out=out[out["Symbol"].str.fullmatch(r"[A-Z]{1,5}(-[A-Z])?",na=False)]
    out=out[~out["name"].astype(str).str.contains(r"ETF|ETN|Exchange.Traded|Warrant|Preferred|Depositary|Units|Rights",case=False,regex=True,na=False)]
    out=out.rename(columns={"name":"Security","Sector Source":"Sector","Industry Source":"Industry"})
    out=out.sort_values("Market Cap",ascending=False)
    gics=sp[["Symbol","Sector","Industry"]].rename(columns={"Sector":"GICS Sector","Industry":"GICS Industry"})
    out=out.merge(gics,on="Symbol",how="left")
    out["Sector"]=out["GICS Sector"].fillna(out["Sector"])
    out["Industry"]=out["GICS Industry"].fillna(out["Industry"])
    return out


def rotation_fig(c):
    # x = 20d relative return vs SPY; y = change in 5d relative return, vs prior 5d.
    # This is a transparent custom rotation proxy, NOT an official RRG / JdK measure.
    fig=go.Figure()
    qcolors={"Leading":"#25be77","Improving":"#4c9fdb","Weakening":"#f0b75c","Lagging":"#e75d63"}
    for x0,x1,y0,y1,color in [(-25,0,0,25,"#142b3b"),(0,25,0,25,"#143025"),
                               (-25,0,-25,0,"#302022"),(0,25,-25,0,"#352c20")]:
        fig.add_shape(type="rect",x0=x0,x1=x1,y0=y0,y1=y1,fillcolor=color,line_width=0,layer="below")
    for label,x,y in [("IMPROVING",-23,22),("LEADING",22,22),("LAGGING",-23,-22),("WEAKENING",22,-22)]:
        fig.add_annotation(x=x,y=y,text=label,showarrow=False,font=dict(color="#8a9aaf",size=13),opacity=.82)
    rows=[]
    for etf,sector in SPDR.items():
        current_x=period_rs(c,21).get(etf,np.nan)
        now=period_rs(c,5).get(etf,np.nan)
        prev=period_rs(c,5,offset=5).get(etf,np.nan)
        dy=now-prev
        if not np.isfinite(current_x) or not np.isfinite(dy):continue
        status=("Leading" if dy>=0 else "Weakening") if current_x>=0 else ("Improving" if dy>=0 else "Lagging")
        rows.append({"ETF":etf,"Sector":sector,"RS 1M %":current_x,"RS momentum pp":dy,"Rotation":status})
        # Weekly relative-performance trail; each point uses information available at the offset.
        trail=[]
        for off in (15,10,5,0):
            xx=period_rs(c,21,offset=off).get(etf,np.nan)
            yy=period_rs(c,5,offset=off).get(etf,np.nan)-period_rs(c,5,offset=off+5).get(etf,np.nan)
            if np.isfinite(xx) and np.isfinite(yy):trail.append((xx,yy))
        if len(trail)>1:
            fig.add_trace(go.Scatter(x=[a for a,b in trail],y=[b for a,b in trail],mode="lines+markers",
                marker=dict(size=[4]*(len(trail)-1)+[8],color=qcolors[status]),
                line=dict(color=qcolors[status],width=2),name=etf,showlegend=False,
                hovertemplate=etf+"<br>20D RS %{x:.2f}<br>RS acceleration %{y:.2f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=[current_x],y=[dy],mode="markers+text",text=[etf],customdata=[etf],textposition="top center",
            textfont=dict(size=11,color="#eef5fa"),marker=dict(size=16,color=qcolors[status],line=dict(color="#d2e3ee",width=1)),
            name=etf,showlegend=False,hovertemplate=f"{etf} · {sector}<br>RS 1M %{{x:.2f}}<br>Momentum %{{y:.2f}} pp<extra></extra>"))
    fig.add_hline(y=0,line_width=1,line_color="#8291a2")
    fig.add_vline(x=0,line_width=1,line_color="#8291a2")
    xs=[r["RS 1M %"] for r in rows];ys=[r["RS momentum pp"] for r in rows]
    marginx=max(7,max((abs(v) for v in xs),default=7)*1.35)
    marginy=max(7,max((abs(v) for v in ys),default=7)*1.35)
    fig.update_layout(paper_bgcolor=BG,plot_bgcolor=BG,font=dict(color="#c3d2e2"),
        margin=dict(l=12,r=12,t=10,b=15),height=580,
        xaxis=dict(title="20-day RS vs SPY (%)",range=[-marginx,marginx],zeroline=False,gridcolor="#2a3645"),
        yaxis=dict(title="5-day RS acceleration (pp)",range=[-marginy,marginy],zeroline=False,gridcolor="#2a3645"))
    return fig,pd.DataFrame(rows)



# ---------- Market breadth and macro ----------
def make_breadth(close, volume, membership):
    """Breadth calculated from *available members of the chosen universe*.

    Uses close-to-close daily bars, not exchange-wide advance/decline feeds.
    Historical series is survivorship-biased to today's membership.
    """
    if close.empty or len(close)<255:
        return {},pd.DataFrame(),pd.DataFrame()
    members=membership[["Symbol","Sector"]].drop_duplicates("Symbol")
    names=[s for s in members.Symbol if s in close.columns and s!="SPY"]
    if not names:return {},pd.DataFrame(),pd.DataFrame()
    c=close[names].apply(pd.to_numeric,errors="coerce")
    last2=c.iloc[-2:]
    current=last2.iloc[-1]
    preceding=last2.iloc[-2]
    valid=(current.gt(0)&preceding.gt(0)&current.notna()&preceding.notna())
    d=(current-preceding).where(valid)
    advances=int((d>0).sum());declines=int((d<0).sum());unchanged=int((d==0).sum())
    coverage=int(valid.sum())
    ma_rates={}
    for w in (20,50,200):
        ma=c.rolling(w,min_periods=w).mean().iloc[-1]
        eligible=current.notna()&ma.notna()&(ma>0)
        ma_rates[w]=(float((current[eligible]>ma[eligible]).mean()*100) if eligible.any() else float('nan'),int(eligible.sum()))
    prev_52_high=c.shift(1).rolling(252,min_periods=240).max().iloc[-1]
    prev_52_low=c.shift(1).rolling(252,min_periods=240).min().iloc[-1]
    eligible_hl=current.notna()&prev_52_high.notna()&prev_52_low.notna()
    new_highs=int(((current>prev_52_high)&eligible_hl).sum())
    new_lows=int(((current<prev_52_low)&eligible_hl).sum())
    v=volume.reindex(index=c.index,columns=c.columns).iloc[-1]
    advancing_volume=v.where(d>0).sum(min_count=1)
    declining_volume=v.where(d<0).sum(min_count=1)
    adv_vol_ratio=float(advancing_volume/declining_volume) if pd.notna(declining_volume) and declining_volume>0 else float('nan')
    changed=c.diff()
    net=(changed.gt(0).sum(axis=1)-changed.lt(0).sum(axis=1)).rename("Net advances")
    valid_n=(c.notna()&c.shift(1).notna()).sum(axis=1)
    ad_line=net.cumsum().rename("A/D cumulative (base 0)")
    mc=net.ewm(span=19,adjust=False).mean()-net.ewm(span=39,adjust=False).mean()
    ma50=c.rolling(50,min_periods=50).mean()
    ma200=c.rolling(200,min_periods=200).mean()
    coverage_50=(ma50.notna()&c.notna()).sum(axis=1)
    coverage_200=(ma200.notna()&c.notna()).sum(axis=1)
    pct50=100*(c>ma50).sum(axis=1)/coverage_50.replace(0,np.nan)
    pct200=100*(c>ma200).sum(axis=1)/coverage_200.replace(0,np.nan)
    chart=pd.DataFrame({"Net advancers":net,"A/D line":ad_line,"McClellan-style":mc,
                        "Above MA50 %":pct50,"Above MA200 %":pct200,"Coverage":valid_n})
    chart=chart.tail(126)
    mem=members.set_index("Symbol").reindex(names)
    group=pd.DataFrame({"Symbol":names,"Sector":mem["Sector"].values,
                        "Advance":d.reindex(names).gt(0).values,
                        "Decline":d.reindex(names).lt(0).values,
                        "Above MA50":(current>ma50.iloc[-1]).reindex(names).values,
                        "Valid MA50":(current.notna()&ma50.iloc[-1].notna()).reindex(names).values})
    by_sector=[]
    for sec,g in group.groupby("Sector",dropna=False):
        denom=int(g["Valid MA50"].sum())
        by_sector.append({"Sector":sec,"Stocks":len(g),"Advancing":int(g["Advance"].sum()),
                          "Declining":int(g["Decline"].sum()),
                          "Above MA50 %":100*int(g["Above MA50"].sum())/denom if denom else np.nan,
                          "Coverage MA50":denom})
    summary={"Coverage today":coverage,"Total in universe":len(names),
             "Advances":advances,"Declines":declines,"Unchanged":unchanged,
             "A/D ratio":advances/declines if declines else np.nan,
             "New 52W highs":new_highs,"New 52W lows":new_lows,"52W coverage":int(eligible_hl.sum()),
             "Adv/Decl volume":adv_vol_ratio,"McClellan-style":float(mc.iloc[-1]),
             "MA percentages":ma_rates,"Date":str(pd.Timestamp(c.index[-1]).date())}
    return summary,chart,pd.DataFrame(by_sector).sort_values("Above MA50 %",ascending=False)


MACRO_GROUPS={
    "Index futures": {"ES=F":"S&P 500 E-mini","NQ=F":"Nasdaq 100 E-mini", "YM=F":"Dow E-mini", "RTY=F":"Russell 2000 E-mini"},
    "Precious & industrial metals": {"GC=F":"Gold","SI=F":"Silver","HG=F":"Copper","PL=F":"Platinum","PA=F":"Palladium"},
    "Energy & agriculture": {"CL=F":"WTI Crude","BZ=F":"Brent Crude","NG=F":"Natural Gas","ZC=F":"Corn","ZW=F":"Wheat","ZS=F":"Soybeans"},
    "Treasury futures": {"ZT=F":"2Y Note futures","ZF=F":"5Y Note futures","ZN=F":"10Y Note futures","ZB=F":"30Y Bond futures"},
    "US interest-rate yields": {"^IRX":"13-week T-bill","^FVX":"5-year Treasury","^TNX":"10-year Treasury","^TYX":"30-year Treasury"},
}
MACRO_SYMBOLS={k: (grp,label) for grp,group in MACRO_GROUPS.items() for k,label in group.items()}
MACRO_YIELD={"^IRX","^FVX","^TNX","^TYX"}


FRED_RATES = {"DFF":"Effective Fed funds rate", "SOFR":"SOFR overnight",
              "DGS2":"Treasury 2Y", "DGS5":"Treasury 5Y",
              "DGS10":"Treasury 10Y", "DGS30":"Treasury 30Y"}


@st.cache_data(ttl=6*3600,show_spinner=False)
def fred_rates():
    """No-key FRED graph CSV; optional and always graceful on 403/timeout.

    Daily published interest rates, not streaming tradable quotes.
    """
    try:
        url="https://fred.stlouisfed.org/graph/fredgraph.csv"
        response=requests.get(url,params={"id":",".join(FRED_RATES),"cosd":"2025-01-01"},
                              headers=HEADERS,timeout=(3,8))
        response.raise_for_status()
        df=pd.read_csv(io.StringIO(response.text),parse_dates=[0],na_values=[".",""])
        if df.empty:return pd.DataFrame()
        df=df.set_index(df.columns[0])
        df.index=pd.to_datetime(df.index,errors="coerce")
        df=df[~df.index.isna()].sort_index()
        available=[sym for sym in FRED_RATES if sym in df]
        return df[available].apply(pd.to_numeric,errors="coerce")
    except Exception:
        return pd.DataFrame()


def fred_rates_table(data):
    rows=[]
    if data.empty:return pd.DataFrame()
    for sym,label in FRED_RATES.items():
        if sym not in data:continue
        observations=data[sym].dropna()
        if observations.empty:continue
        last=float(observations.iloc[-1]);prior=float(observations.iloc[-2]) if len(observations)>1 else np.nan
        rows.append({"Series":sym,"Rate":label,"Yield / rate %":last,
                    "Δ prior observation (pp)":last-prior if np.isfinite(prior) else np.nan,
                    "Reported":str(pd.Timestamp(observations.index[-1]).date()),
                    "Source":"https://fred.stlouisfed.org/series/"+sym})
    return pd.DataFrame(rows)


def macro_snapshot(c):
    """Last observed prices and returns for available Yahoo futures/rates data."""
    if c.empty:return pd.DataFrame()
    out=[]
    for sym,(group,label) in MACRO_SYMBOLS.items():
        if sym not in c.columns:continue
        series=pd.to_numeric(c[sym],errors="coerce").dropna()
        if len(series)<2:continue
        current=float(series.iloc[-1]);prev=float(series.iloc[-2])
        if current<=0 or prev<=0:continue
        is_yield=sym in MACRO_YIELD
        # Yahoo's current Treasury yield series ^IRX/^FVX/^TNX/^TYX
        # are already quoted in percent units (e.g. ^TNX 4.929 means 4.929%).
        rate=current
        change=(current-prev) if is_yield else (current/prev-1)*100
        week=(current/float(series.iloc[-6])-1)*100 if len(series)>5 and not is_yield else np.nan
        month=(current/float(series.iloc[-22])-1)*100 if len(series)>21 and not is_yield else np.nan
        out.append({"Group":group,"Ticker":sym,"Instrument":label,"Last":rate,
                    "1D change":change,"1W %":week,"1M %":month,
                    "Units":"% yield" if is_yield else "contract price",
                    "As of":str(pd.Timestamp(series.index[-1]).date()),
                    "TradingView":"https://www.tradingview.com/chart/?symbol="+quote(sym,safe="")})
    return pd.DataFrame(out)

# ---------- Header / global filters ----------
st.markdown("""<div class='rsm-brand'>
<span class='rsm-brandmark'>▥</span><div><div class='rsm-title'>RS MATRIX <span style='color:#57bf94'>/</span> MARKET LEADERSHIP</div>
<div class='rsm-subtitle'>S&P 500 · Sector SPDR · Breadth · Commodities · Futures · Rates</div></div>
<span class='rsm-chip'>FREE DAILY DATA</span></div>""",unsafe_allow_html=True)

# A dedicated navigation row avoids six workspaces wrapping inside a narrow column.
# A bubble click navigates to the same app with a chart query parameter.
# Consume it immediately so closing the modal cannot leave a stale popup URL.
_rsm_incoming_symbol=valid_ticker(st.query_params.get("rsm_chart",""))
_rsm_incoming_view=st.query_params.get("rsm_view","RS MATRIX")
_rsm_incoming_window=st.query_params.get("rsm_window","1W")
if "rsm_chart" in st.query_params:
    st.query_params.clear()
if _rsm_incoming_symbol:
    st.session_state["_rsm_popup_request"]=_rsm_incoming_symbol
view=st.radio("Workspace",WORKSPACES,
              index=WORKSPACES.index(_rsm_incoming_view) if _rsm_incoming_view in WORKSPACES else 0,
              horizontal=True,label_visibility="collapsed")
bar1,bar3,bar4=st.columns([2.5,1.35,1.2],gap="large")
with bar1:
    universe_choice=st.selectbox("Universe",["S&P 500","NYSE + Nasdaq (top N)"],
                                help="Used for RS Matrix, Market Breadth and Minervini Scanner; SPDR and Macro data are independent.")
with bar3:
    period=st.selectbox("RS WINDOW",PERIODS,
                        index=PERIODS.index(_rsm_incoming_window) if _rsm_incoming_window in PERIODS else 1,
                        help="Used for RS Matrix, SPDR ETF strength and scanner.")
with bar4:
    st.write(" ")
    refresh=st.button("↻ Refresh prices",type="primary",use_container_width=True)

if refresh:
    prices.clear()

# Sector modules should NOT incur hundreds of quote downloads from the stock scanner.
if view in ("RS MATRIX","MINERVINI SCANNER","MARKET BREADTH"):
    try:
        sp=get_sp500()
    except Exception as exc:
        st.error("Cannot load S&P 500 list: " + str(exc));st.stop()
    try:
        snap=get_snapshot()
    except Exception as exc:
        snap=None
        st.warning("Market-cap snapshot unavailable: securities without cap data will be excluded from cap-tier matrix. " + str(exc)[:160])

    all_symbols=market_scope(sp,snap,universe_choice=="S&P 500")
    if universe_choice!="S&P 500":
        n=st.slider("NYSE + Nasdaq sample (ranked by available market cap)",100,2000,500,100)
        all_symbols=all_symbols.head(n)
    universe=all_symbols.copy()
    with st.spinner(f"Loading price history for {len(universe)} tickers (Yahoo Finance, cached 30 minutes)…"):
        close,volume=prices(tuple(universe.Symbol.tolist()))
    if close.empty or "SPY" not in close:
        st.error("Yahoo Finance temporarily unavailable/rate-limited. Try later or reduce the universe size.")
        st.stop()
    days=lookback_for(period,close.index)
    data=build_signals(close,volume,days,universe)
    if data.empty:
        st.error("Insufficient historical price data for this scan.");st.stop()
    k1,k2,k3,k4,k5=st.columns(5)
    k1.metric("Valid tickers",f"{len(data):,}")
    k2.metric("Outperform SPY",f"{(data['RS %']>0).sum():,}")
    k3.metric("RS accelerating",f"{(data['RS acceleration']>0).sum():,}")
    k4.metric("Minervini candidates",f"{data['Minervini candidate'].sum():,}")
    k5.metric("Price date",str(pd.Timestamp(close.index[-1]).date()))
    st.markdown("<div class='rsm-note'>Adjusted daily close · relative returns vs SPY · market caps: Nasdaq snapshot (not intraday) · RVOL/U-D estimates from daily bars · no guaranteed real-time consolidated feed</div>",unsafe_allow_html=True)
else:
    st.markdown("<div class='rsm-note'>Sector ETFs are loaded independently of the stock universe · daily Yahoo Finance bars · holdings may update on a different date</div>",unsafe_allow_html=True)
st.divider()

if view=="RS MATRIX":
    sub1,sub2,sub3=st.columns([1.85,1.0,1.4])
    with sub1:
        sectors=sorted(data["Sector"].dropna().unique().tolist())
        sector_name=st.selectbox("Sector",["All sectors"]+sectors,index=0)
    with sub2:
        show_count=st.select_slider("Max bubbles",options=[50,80,120,160,250,500],value=160)
    with sub3:
        search=st.text_input("Find ticker",placeholder="AAPL, NVDA, PLTR…").upper().strip()
    with st.expander("Additional matrix filters",expanded=False):
        filt1,filt2,filt3=st.columns(3)
        with filt1: positive=st.checkbox("Only outperforming SPY",value=False)
        with filt2: improving=st.checkbox("Only RS accelerating",value=False)
        with filt3: only_trend=st.checkbox("Only MA50 > MA200 + price above MA50",value=False)
    shown=data.copy()
    if sector_name!="All sectors":shown=shown[shown["Sector"]==sector_name]
    if positive:shown=shown[shown["RS %"]>0]
    if improving:shown=shown[shown["RS acceleration"]>0]
    if only_trend:shown=shown[shown["Trend"]]
    if search:shown=shown[shown["Symbol"].str.contains(search,regex=False)]
    left,right=st.columns([1.2,3.6],gap="small")
    with left:
        st.markdown(sector_rail(data),unsafe_allow_html=True)
        st.caption("Sector RS = unweighted mean of available constituent RS, not an ETF return. Ranked over the selected window.")
    with right:
        st.markdown("<div class='rsm-head'>SECTOR → INDUSTRY × MARKET CAP · "+html.escape(period)+" vs SPY</div>",unsafe_allow_html=True)
        st.markdown(bubbles_matrix(shown,max_symbols=show_count,rs_window=period),unsafe_allow_html=True)
        missing_cap=int((~shown["Cap tier"].isin(TIER_ORDER)).sum())
    st.markdown(f"<div class='rsm-foot'>Green: outperform SPY · Red: underperform · grouped by sector and industry · hover for exact data · hover a bubble to open the full chart, or click on touch screens. <b>{missing_cap}</b> symbols without market cap excluded from matrix (still eligible for scanner).</div>",unsafe_allow_html=True)
    st.markdown("<div class='rsm-section'>Quick leadership list · sortable</div>",unsafe_allow_html=True)
    s1,s2,s3,s4=st.columns([1.2,1.2,1.3,1.0],gap="small")
    with s1:
        lead_sort=st.selectbox("Sort leaders by",["RS %","RS acceleration","RVOL","U/D proxy","Price","Market Cap"],key="leaders_sort")
    with s2:
        lead_rvol=st.number_input("RVOL ≥",min_value=0.0,max_value=20.0,value=0.0,step=.1,key="leaders_min_rvol")
    with s3:
        lead_ud=st.number_input("U/D proxy ≥",min_value=0.0,max_value=20.0,value=0.0,step=.1,key="leaders_min_ud")
    with s4:
        lead_limit=st.selectbox("Rows",[35,75,150,300],key="leaders_rows")
    top=shown.loc[(shown["RVOL"]>=lead_rvol)&(shown["U/D proxy"]>=lead_ud)].copy()
    top=top.sort_values(lead_sort,ascending=False,na_position="last").head(lead_limit)
    top["TradingView"]=top.Symbol.map(lambda s:"https://www.tradingview.com/chart/?symbol="+quote(str(s),safe=""))
    st.caption(f"{len(top)} symbols shown · Click the RS, RVOL or other column header to re-sort directly in the list")
    dark_table(top[["Symbol","Security","Sector","Industry","Cap tier","RS %","RS acceleration","RVOL","U/D proxy","TradingView"]],
        key="leadership_results",ticker_col="Symbol",
        hide_index=True,use_container_width=True,
        column_config={"RS %":st.column_config.NumberColumn(format="%.2f%%"),
                       "RS acceleration":st.column_config.NumberColumn("RS accel. (pp)",format="%+.2f"),
                       "RVOL":st.column_config.NumberColumn(format="%.2f"),
                       "TradingView":st.column_config.LinkColumn("Chart",display_text="Open ↗")})

elif view=="SECTOR SPDR":
    st.markdown("<div class='rsm-section'>SELECT SECTOR SPDR · 11 ETFs + TOP 10 HOLDINGS</div><div class='rsm-small'>Compare sector returns vs SPY and each ETF's largest reported holdings. Holdings source date must be verified with provider.</div>",unsafe_allow_html=True)
    sector_etfs=list(SPDR)
    with st.spinner("Loading sector ETF histories…"):
        etf_close,_=prices(tuple(sector_etfs))
    if etf_close.empty or "SPY" not in etf_close:
        st.warning("Sector ETF prices unavailable from Yahoo Finance.")
    else:
        etf_rs=period_rs(etf_close,lookback_for(period,etf_close.index))
        ranking=pd.DataFrame({"ETF":sector_etfs,"Sector":[SPDR[t] for t in sector_etfs]})
        ranking["RS vs SPY %"]=ranking.ETF.map(etf_rs)
        ranking=ranking.sort_values("RS vs SPY %",ascending=False)
        a,b=st.columns([1.85,1],gap="medium")
        with a:
            st.markdown("<div class='rsm-head'>SECTOR ETF STRENGTH · FULL NAMES</div>",unsafe_allow_html=True)
            st.markdown(spdr_rank_html(ranking),unsafe_allow_html=True)
        with b:
            dark_table(ranking,key="spdr_sector_rank",ticker_col="ETF",hide_index=True,use_container_width=True,height=510,
                column_config={"RS vs SPY %":st.column_config.NumberColumn(format="%+.2f")})
    etf_pick=st.selectbox("Top holdings for sector",["All 11 ETFs"]+[f"{s} · {SPDR[s]}" for s in SPDR],index=1)
    picks=sector_etfs if etf_pick=="All 11 ETFs" else [etf_pick.split(" · ")[0]]
    with st.spinner("Loading reported Top 10 holdings…"):
        blocks=[];miss=[]
        for etf in picks:
            h,source=spdr_holdings(etf)
            if h.empty:miss.append(etf);continue
            h=h.copy();h["ETF"]=etf;h["Sector"]=SPDR[etf];h["Holdings source"]=source
            blocks.append(h)
    if miss:st.warning("Holdings not available for: "+", ".join(miss)+". No substitute holdings are invented.")
    if blocks:
        holdings=pd.concat(blocks,ignore_index=True)
        with st.spinner("Loading daily history for holdings…"):
            hclose,_=prices(tuple(list(SPDR)+list(holdings.Symbol.dropna().unique())))
        rs=period_rs(hclose,lookback_for(period,hclose.index))
        holdings["RS vs SPY %"]=holdings.Symbol.map(rs)
        holdings["RS vs ETF (pp)"]=holdings.apply(lambda r: r["RS vs SPY %"]-rs.get(r["ETF"],np.nan),axis=1)
        holdings["TradingView"]=holdings.Symbol.map(lambda s:"https://www.tradingview.com/chart/?symbol="+quote(str(s),safe=""))
        holdings=holdings.sort_values(["ETF","Weight %"],ascending=[True,False])
        st.markdown("<div class='rsm-section'>Top 10 holdings · relative leadership</div>",unsafe_allow_html=True)
        color_mode=st.radio("Color the bubbles by",["RS vs SPY %","RS vs ETF (pp)"],horizontal=True,
                            help="RS vs ETF is the difference, in percentage points, between the stock and ETF relative performance versus SPY.")
        st.markdown(spdr_bubbles(holdings,color_mode,rs_window=period),unsafe_allow_html=True)
        st.caption("Bubble labels are stock tickers · hover to open a chart popup · sorted by holding weight, not by RS.")
        holdings_show=holdings[["ETF","Sector","Symbol","Weight %","RS vs SPY %","RS vs ETF (pp)","TradingView","Holdings source"]]
        dark_table(holdings_show,key="spdr_holdings_list",ticker_col="Symbol",use_container_width=True,hide_index=True,height=min(620,max(230,34*len(holdings)+40)),
            column_config={"Weight %":st.column_config.NumberColumn(format="%.2f%%"),
                "RS vs SPY %":st.column_config.NumberColumn(format="%+.2f"),
                "RS vs ETF (pp)":st.column_config.NumberColumn(format="%+.2f"),
                "TradingView":st.column_config.LinkColumn("Chart",display_text="Open ↗")})
        st.download_button("⬇ Export SPDR holdings CSV",data=holdings_show.to_csv(index=False).encode("utf-8"),
            file_name="sector_spdr_top10_rs.csv",mime="text/csv")
        st.caption("ETF membership is sorted by fund weight; it is NOT a list of top performers. RS vs ETF (pp) = difference of two RS-versus-SPY percentages. Holdings may be from a different date than prices. Verify official ETF files at ssga.com.")

elif view=="SECTOR ROTATION":
    st.markdown("<div class='rsm-section'>SECTOR ROTATION · four-quadrant leadership map</div><div class='rsm-small'>Leading / Improving / Weakening / Lagging based on 20-day relative performance and change in weekly RS.</div>",unsafe_allow_html=True)
    with st.spinner("Loading sector rotation histories…"):
        etf_close,_=prices(tuple(SPDR))
    if etf_close.empty or "SPY" not in etf_close or len(etf_close)<50:
        st.warning("Insufficient daily data for sector rotation.")
    else:
        fig,rot=rotation_fig(etf_close)
        rotation_event=st.plotly_chart(fig,use_container_width=True,theme=None,
            key="rotation_bubble_plot",on_select="rerun",selection_mode="points")
        selected_points=rotation_event.selection.points
        if selected_points:
            selected_point=selected_points[0]
            raw_ticker=selected_point.get("customdata") or selected_point.get("text") or ""
            if isinstance(raw_ticker,(list,tuple)):
                raw_ticker=raw_ticker[0] if raw_ticker else ""
            selected_ticker=valid_ticker(raw_ticker)
            selected_marker=(selected_point.get("curve_number"),selected_point.get("point_index"),selected_ticker)
            if selected_ticker and st.session_state.get("_rsm_rotation_last_selection")!=selected_marker:
                st.session_state["_rsm_popup_request"]=selected_ticker
            st.session_state["_rsm_rotation_last_selection"]=selected_marker
        else:
            st.session_state.pop("_rsm_rotation_last_selection",None)
        st.caption("Click a sector ETF dot or hover an ETF ticker in the table below to open its chart.")
        if not rot.empty:
            a,b,c,d=st.columns(4)
            for widget,status in zip((a,b,c,d),("Leading","Improving","Weakening","Lagging")):
                widget.metric(status,int((rot.Rotation==status).sum()))
            rot=rot.sort_values("RS 1M %",ascending=False)
            dark_table(rot,key="rotation_results",ticker_col="ETF",use_container_width=True,hide_index=True,
                column_config={"RS 1M %":st.column_config.NumberColumn(format="%+.2f"),
                               "RS momentum pp":st.column_config.NumberColumn(format="%+.2f")})
        st.info("Custom rotation proxy — NOT an official RRG/JdK RS-Ratio or RS-Momentum. X: 21-session ETF return vs SPY. Y: latest 5-session RS minus preceding 5-session RS (percentage points). Trails are weekly observations, not predictions.")

elif view=="MARKET BREADTH":
    st.markdown("<div class='rsm-section'>MARKET BREADTH · participation inside selected universe</div>",unsafe_allow_html=True)
    st.markdown("<div class='rsm-small'>S&P 500 or selected NYSE/Nasdaq sample · daily breadth from individual adjusted closes · not official exchange-wide NYSE/Nasdaq internals.</div>",unsafe_allow_html=True)
    breadth,chart,by_sector=make_breadth(close,volume,universe)
    if not breadth:
        st.warning("Insufficient coverage for market breadth. Historical daily data for at least 255 sessions is required.")
    else:
        a,b,c,d,e=st.columns(5)
        a.metric("Advancing",f"{breadth['Advances']:,}")
        b.metric("Declining",f"{breadth['Declines']:,}")
        c.metric("A/D ratio",f"{breadth['A/D ratio']:.2f}" if pd.notna(breadth['A/D ratio']) else "—")
        d.metric("52W highs / lows",f"{breadth['New 52W highs']} / {breadth['New 52W lows']}")
        e.metric("Valid prices",f"{breadth['Coverage today']} / {breadth['Total in universe']}")
        p,q,r=st.columns(3)
        for box,w in zip((p,q,r),(20,50,200)):
            pct,denom=breadth['MA percentages'][w]
            box.metric(f"Above MA{w}",f"{pct:.1f}%" if pd.notna(pct) else "—",help=f"Calculated across {denom} stocks with sufficient history")
        ratio=breadth['Adv/Decl volume']
        st.markdown(f"<span class='rsm-pill'>Advancing/declining daily volume: {ratio:.2f}×</span>" if pd.notna(ratio) else "<span class='rsm-pill'>Advancing/declining daily volume: unavailable</span>",unsafe_allow_html=True)
        st.markdown(f"<span class='rsm-pill'>Breadth as of {breadth['Date']} · 52W eligible: {breadth['52W coverage']}</span>",unsafe_allow_html=True)
        cc1,cc2=st.columns(2,gap="medium")
        with cc1:
            fig=go.Figure()
            fig.add_trace(go.Scatter(x=chart.index,y=chart['Above MA50 %'],name='Above MA50',line=dict(color='#34c385',width=2)))
            fig.add_trace(go.Scatter(x=chart.index,y=chart['Above MA200 %'],name='Above MA200',line=dict(color='#5aa7e4',width=2)))
            fig.update_layout(title="% of stocks above moving averages",paper_bgcolor=PANEL,plot_bgcolor=PANEL,font=dict(color='#d6e2ef'),height=350,margin=dict(l=25,r=10,t=48,b=22),yaxis=dict(title='%',range=[0,100],gridcolor=LINE),xaxis=dict(gridcolor=LINE),legend=dict(orientation='h',y=1.04))
            st.plotly_chart(fig,use_container_width=True,theme=None)
        with cc2:
            fig=go.Figure()
            fig.add_trace(go.Scatter(x=chart.index,y=chart['A/D line'],name='Cumulative A/D (relative baseline)',line=dict(color='#f0bd62',width=2)))
            fig.update_layout(title="Advance–decline line (current universe)",paper_bgcolor=PANEL,plot_bgcolor=PANEL,font=dict(color='#d6e2ef'),height=350,margin=dict(l=25,r=10,t=48,b=22),xaxis=dict(gridcolor=LINE),yaxis=dict(gridcolor=LINE))
            st.plotly_chart(fig,use_container_width=True,theme=None)
        cc3,cc4=st.columns([1.15,1],gap="medium")
        with cc3:
            fig=go.Figure(go.Bar(x=chart.index,y=chart['Net advancers'],marker_color=['#24bd76' if x>=0 else '#f05256' for x in chart['Net advancers']]))
            fig.update_layout(title="Daily net advancers (advances − declines)",paper_bgcolor=PANEL,plot_bgcolor=PANEL,font=dict(color='#d6e2ef'),height=330,margin=dict(l=25,r=10,t=45,b=22),xaxis=dict(gridcolor=LINE),yaxis=dict(gridcolor=LINE))
            st.plotly_chart(fig,use_container_width=True,theme=None)
        with cc4:
            st.markdown("<div class='rsm-head'>BREADTH BY SECTOR · % ABOVE MA50</div>",unsafe_allow_html=True)
            dark_table(by_sector,key="breadth_sector_table",hide_index=True,use_container_width=True,height=335,
                column_config={'Above MA50 %':st.column_config.ProgressColumn('Above MA50 %',min_value=0,max_value=100,format='%.1f%%')})
        st.caption("Definitions: advances/declines vs prior daily close; 52-week extremes vs prior 252 sessions; A/D line and 19/39 EMA oscillator calculated from available current-universe constituents. Historical breadth has survivorship bias; incomplete histories are excluded per indicator. This is not exchange-wide NYSE/Nasdaq advance/decline data.")

elif view=="MACRO MARKETS":
    st.markdown("<div class='rsm-section'>MACRO MARKETS · futures, commodities, metals & rates</div>",unsafe_allow_html=True)
    st.markdown("<div class='rsm-small'>Yahoo Finance daily settlements/quotes; contracts may be delayed and each symbol can have a different observation date. Futures prices are continuous contract proxies, not executable quotes.</div>",unsafe_allow_html=True)
    categories=list(MACRO_GROUPS)
    selection=st.selectbox("Asset class",["All markets"]+categories)
    symbols=list(MACRO_SYMBOLS)
    with st.spinner("Loading cached daily futures and yields history…"):
        mc,_=prices(tuple(symbols))
    market=macro_snapshot(mc)
    if selection in ("All markets","US interest-rate yields"):
        st.markdown("<div class='rsm-section'>US reference rates & Treasury yield curve · FRED</div>",unsafe_allow_html=True)
        rates=fred_rates()
        rates_tbl=fred_rates_table(rates)
        if not rates_tbl.empty:
            dark_table(rates_tbl,key="rates_table",ticker_col="Series",hide_index=True,use_container_width=True,
                column_config={"Yield / rate %":st.column_config.NumberColumn(format="%.3f%%"),
                    "Δ prior observation (pp)":st.column_config.NumberColumn(format="%+.3f"),
                    "Source":st.column_config.LinkColumn("FRED",display_text="Open ↗")})
            yield_curve=[(2,'DGS2'),(5,'DGS5'),(10,'DGS10'),(30,'DGS30')]
            xp,yp=[],[]
            for maturity,sym in yield_curve:
                if sym in rates and rates[sym].notna().any():
                    xp.append(maturity);yp.append(float(rates[sym].dropna().iloc[-1]))
            if len(xp)>=2:
                fig=go.Figure(go.Scatter(x=xp,y=yp,mode='lines+markers+text',
                    text=[f'{v:.2f}%' for v in yp],textposition='top center',
                    line=dict(color='#5bb7eb',width=3),marker=dict(size=11)))
                fig.update_layout(paper_bgcolor=PANEL,plot_bgcolor=PANEL,font=dict(color='#d6e2ef'),height=290,
                    margin=dict(l=35,r=15,t=22,b=28),xaxis=dict(title='Maturity (years)',tickvals=xp,gridcolor=LINE),
                    yaxis=dict(title='Yield %',gridcolor=LINE))
                st.plotly_chart(fig,use_container_width=True,theme=None)
            st.caption("FRED daily published rates (not real-time). Latest observation date is shown separately for each series. Data may be revised; source: fred.stlouisfed.org.")
        else:
            st.info("FRED reference-rate feed temporarily unavailable; Yahoo Treasury yield proxies are still displayed below.")
    if selection!="All markets" and not market.empty:
        market=market[market['Group']==selection]
    if market.empty:
        st.warning("Macro data unavailable from Yahoo Finance. Try refreshing later; missing symbols are not fabricated.")
    else:
        dark_table(market,key="macro_results",ticker_col="Ticker",hide_index=True,use_container_width=True,height=min(720,60+35*len(market)),
            column_config={'Last':st.column_config.NumberColumn(format='%.3f'),
                '1D change':st.column_config.NumberColumn('1D % / yield pp',format='%+.3f'),
                '1W %':st.column_config.NumberColumn(format='%+.2f'),
                '1M %':st.column_config.NumberColumn(format='%+.2f'),
                'TradingView':st.column_config.LinkColumn('Chart',display_text='Open ↗')})
        st.markdown("<div class='rsm-section'>Instrument chart</div>",unsafe_allow_html=True)
        pick=st.selectbox("Instrument",market['Ticker'].tolist(),format_func=lambda sym:f"{MACRO_SYMBOLS[sym][1]} ({sym})")
        if pick in mc:
            src=mc[pick].dropna().tail(130)
            if not src.empty:
                value=src
                fig=go.Figure(go.Scatter(x=value.index,y=value.values,mode='lines',line=dict(color='#48c89b',width=2)))
                fig.update_layout(paper_bgcolor=PANEL,plot_bgcolor=PANEL,font=dict(color='#d6e2ef'),height=370,
                                  margin=dict(l=25,r=15,t=10,b=25),xaxis=dict(gridcolor=LINE),
                                  yaxis=dict(title='% (yield)' if pick in MACRO_YIELD else 'Contract price',gridcolor=LINE))
                st.plotly_chart(fig,use_container_width=True,theme=None)
        st.caption("For ^IRX, ^FVX, ^TNX and ^TYX: Yahoo already quotes yields in %, and the 1D change is expressed in percentage points (pp), NOT the percent price return. Other contracts show daily % price change. Data is indicative, not real-time guaranteed.")

elif view=="MY WATCHLIST":
    st.markdown("<div class='rsm-section'>MY WATCHLIST · SHARED BY ALL USERS</div>",unsafe_allow_html=True)
    st.markdown("<div class='rsm-small'>Hover on any symbol to open the full chart and add/remove it. No login; everyone sees the same list and can edit it.</div>",unsafe_allow_html=True)
    watchlist_banner()
    try:
        watch_symbols=watchlist_symbols()
    except Exception as exc:
        st.error('Cannot read the shared watchlist: '+str(exc)[:200])
        watch_symbols=[]
    a,b=st.columns([3,1])
    with a:
        typed=st.text_input('Add ticker manually',placeholder='Example: AAPL, XLK or GLD').strip().upper()
    with b:
        st.write(' ')
        if st.button('＋ Add symbol',type='primary',use_container_width=True):
            try:
                if not valid_ticker(typed):st.warning('Enter a valid ticker.')
                else:
                    added=watchlist_add(typed)
                    if added:st.success(typed+' added to the shared watchlist.')
                    else:st.info(typed+' is already in the watchlist.')
                    st.rerun()
            except Exception as exc:st.error(str(exc))
    if not watch_symbols:
        st.info('The shared watchlist is empty. Hover over any ticker elsewhere in the app, then choose Add to shared watchlist.')
    else:
        left,right=st.columns([1.1,3],gap='large')
        with left:
            to_delete=st.selectbox('Remove ticker',watch_symbols)
            if st.button('Remove selected ticker',use_container_width=True):
                try:
                    watchlist_remove(to_delete)
                    st.rerun()
                except Exception as exc:st.error(str(exc))
            st.metric('Saved symbols',len(watch_symbols))
            st.caption('Ticker list is shared with everyone who visits the app.')
        with right:
            with st.spinner('Loading cached quote history for watchlist…'):
                watch_close,_=prices(tuple(watch_symbols))
            if not watch_close.empty:
                rec=[]
                for sym in watch_symbols:
                    if sym not in watch_close.columns:continue
                    s=watch_close[sym].dropna()
                    if s.empty:continue
                    def pchange(window):
                        if len(s)<=window:return np.nan
                        return (float(s.iloc[-1])/float(s.iloc[-window-1])-1)*100
                    spy=watch_close.get('SPY',pd.Series(dtype=float)).dropna()
                    stock_week=pchange(5)
                    stock_month=pchange(21)
                    spy_week=(float(spy.iloc[-1])/float(spy.iloc[-6])-1)*100 if len(spy)>5 else np.nan
                    spy_month=(float(spy.iloc[-1])/float(spy.iloc[-22])-1)*100 if len(spy)>21 else np.nan
                    rec.append({'Ticker':sym,'Last':float(s.iloc[-1]),'1W %':stock_week,
                                '1M %':stock_month,'RS 1W vs SPY (pp)':stock_week-spy_week,
                                'RS 1M vs SPY (pp)':stock_month-spy_month,
                                'As of':str(pd.Timestamp(s.index[-1]).date())})
                if rec:
                    watch_frame=pd.DataFrame(rec).sort_values('RS 1W vs SPY (pp)',ascending=False)
                    dark_table(watch_frame,key='shared_watchlist_results',ticker_col='Ticker',height=550)
                    st.download_button('⬇ Export shared watchlist CSV',watch_frame.to_csv(index=False).encode('utf-8'),
                                       file_name='shared_rs_watchlist.csv',mime='text/csv')
                else:st.warning('Watchlist symbols found but quotes are temporarily unavailable.')
            else:st.warning('Watchlist quote source unavailable; the saved ticker list is unaffected.')

else:
    st.markdown("<div class='rsm-section'>MINERVINI-STYLE BREAKOUT SCANNER</div><div class='rsm-small'>Screen for positive RS, improving leadership, trend alignment, RVOL and approximate directional volume. No signal guarantees an entry.</div>",unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    with c1: only_rs=st.checkbox("RS vs SPY > 0",value=True)
    with c2: only_acc=st.checkbox("RS accelerating (5D)",value=False)
    with c3: only_break=st.checkbox("New 20-day RS line high",value=False)
    with c4: only_trend=st.checkbox("Trend: price > MA50 > MA200",value=False)
    c5,c6,c7=st.columns(3)
    with c5: min_rvol=st.number_input("Minimum RVOL",min_value=0.0,max_value=20.0,value=1.0,step=.1)
    with c6: min_ud=st.number_input("Minimum U/D proxy",min_value=0.0,max_value=20.0,value=0.0,step=.1)
    with c7: min_cap=st.selectbox("Minimum market cap",["Any","$2B","$10B","$20B","$50B"],index=0)
    name=st.text_input("Search symbol or company",placeholder="e.g. PLTR").strip().upper()
    view_df=data.copy()
    if only_rs:view_df=view_df[view_df["RS %"]>0]
    if only_acc:view_df=view_df[view_df["RS acceleration"]>0]
    if only_break:view_df=view_df[view_df["RS new 20D high"]]
    if only_trend:view_df=view_df[view_df["Trend"]]
    if min_rvol>0:view_df=view_df[view_df["RVOL"]>=min_rvol]
    if min_ud>0:view_df=view_df[view_df["U/D proxy"]>=min_ud]
    if min_cap!="Any":view_df=view_df[view_df["Market Cap"]>=float(min_cap.replace("$","").replace("B",""))*1e9]
    if name:view_df=view_df[view_df["Symbol"].str.contains(name,regex=False)|view_df["Security"].fillna("").str.upper().str.contains(name,regex=False)]
    sort=st.selectbox("Sort results",["RS %","RS acceleration","RVOL","Market Cap","U/D proxy"],index=0)
    view_df=view_df.sort_values(sort,ascending=False).copy()
    view_df["TradingView"]=view_df.Symbol.map(lambda s:"https://www.tradingview.com/chart/?symbol="+quote(str(s),safe=""))
    st.caption(f"{len(view_df)} matches · {int(view_df['Minervini candidate'].sum())} meet the dashboard's simplified Minervini-style composite")
    ordered=["Symbol","Security","Sector","Industry","Cap tier","RS %","RS acceleration","RS new 20D high","Price","MA50","MA200","RVOL","U/D proxy","Trend","Minervini candidate","TradingView"]
    dark_table(view_df[ordered],key="minervini_results",ticker_col="Symbol",hide_index=True,use_container_width=True,height=620,
        column_config={"Symbol":st.column_config.TextColumn("TICKER",width="small"),
            "RS %":st.column_config.NumberColumn(format="%+.2f"),
            "RS acceleration":st.column_config.NumberColumn(format="%+.2f"),
            "Price":st.column_config.NumberColumn(format="$%.2f"),
            "MA50":st.column_config.NumberColumn(format="%.2f"),
            "MA200":st.column_config.NumberColumn(format="%.2f"),
            "RVOL":st.column_config.NumberColumn(format="%.2f"),
            "U/D proxy":st.column_config.NumberColumn(format="%.2f"),
            "TradingView":st.column_config.LinkColumn("Chart",display_text="Open ↗")})
    st.download_button("⬇ Export scanner CSV",view_df.to_csv(index=False).encode("utf-8"),
                       file_name="minervini_rs_scanner.csv",mime="text/csv")
    st.caption("Simplified candidate = RS 1W>0 & RS 1M>0 & Price>MA50>MA200 & RVOL>1 & U/D proxy>1.5. It does NOT implement all original Minervini trend-template/VCP conditions; U/D is NOT the official Up/Down Volume metric.")

# Streamlit components v2: a native event listener catches hovered ticker HTML
# within RS bubbles, SPDR bubbles, rankings and all ticker-bearing result tables.
# After 500ms the existing full-size Streamlit dialog opens automatically.
# Touchscreens can still click the href as a fallback.
RSM_HOVER_JS = r"""
export default function(component) {
  const { setTriggerValue } = component;
  let timer = null;
  let active = null;
  function tickerNode(target) {
    return target && target.closest ? target.closest('[data-rsm-ticker]') : null;
  }
  function onOver(event) {
    if (event.pointerType === 'touch') return;
    const node = tickerNode(event.target);
    if (!node) return;
    const ticker = node.getAttribute('data-rsm-ticker');
    if (!ticker || ticker === active) return;
    clearTimeout(timer);
    active = ticker;
    timer = setTimeout(() => setTriggerValue('hovered', ticker), 500);
  }
  function onOut(event) {
    const node = tickerNode(event.target);
    if (!node || (event.relatedTarget && node.contains(event.relatedTarget))) return;
    clearTimeout(timer);
    active = null;
  }
  document.addEventListener('pointerover', onOver, true);
  document.addEventListener('pointerout', onOut, true);
  // Header sorting is client-side: no server rerun and no loss of hover links.
  function onTableSort(e) {
    const button = e.target && e.target.closest ? e.target.closest('.rsm-sort-head') : null;
    if (!button) return;
    const th=button.closest('th');
    const table=button.closest('table.rsm-list-table');
    if (!table || !th || !table.tBodies.length) return;
    e.preventDefault();
    const col=Number(button.getAttribute('data-rsm-sortcol'));
    if (!Number.isInteger(col)) return;
    const current=th.getAttribute('aria-sort');
    const descending=/RS|RVOL|U\/D|Price|Weight|Cap|Change|Momentum|MA50|MA200/i.test(button.textContent);
    const direction=current==='ascending'?'descending':current==='descending'?'ascending':descending?'descending':'ascending';
    const rows=[...table.tBodies[0].rows];
    const item=(tr)=>tr.cells[col]?.textContent?.trim() || '';
    const numeric=(s)=>{
      const raw=s.replace(/[,%$\s]/g,'').replace(/^[−–]/,'-');
      return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(raw)?Number(raw):null;
    };
    rows.sort((a,b)=>{
      const A=item(a), B=item(b), x=numeric(A), y=numeric(B);
      let d=x!==null&&y!==null?x-y:A.localeCompare(B,undefined,{numeric:true,sensitivity:'base'});
      if (!A || A==='—') d=1;
      if (!B || B==='—') d=-1;
      return direction==='ascending'?d:-d;
    });
    table.querySelectorAll('th').forEach(h=>{
      h.setAttribute('aria-sort','none');
      const arrow=h.querySelector('.rsm-sort-arrow');if(arrow)arrow.textContent='⇅';
    });
    th.setAttribute('aria-sort',direction);
    button.querySelector('.rsm-sort-arrow').textContent=direction==='ascending'?'↑':'↓';
    table.tBodies[0].replaceChildren(...rows);
  }
  document.addEventListener('click',onTableSort,true);
  // Plotly Sector Rotation dots contain the ETF ticker in point.customdata.
  // Avoid attaching to generic plots without that attribute.
  const bound = new WeakSet();
  function bindPlotly() {
    document.querySelectorAll('div.js-plotly-plot').forEach((graph) => {
      if (bound.has(graph) || typeof graph.on !== 'function') return;
      bound.add(graph);
      graph.on('plotly_hover', (evt) => {
        const point = evt && evt.points && evt.points[0];
        const value = point && point.customdata;
        const ticker = Array.isArray(value) ? value[0] : value;
        if (typeof ticker !== 'string' || !/^[A-Z0-9^][A-Z0-9.^=_-]{0,22}$/.test(ticker)) return;
        clearTimeout(timer);
        active=ticker;
        timer=setTimeout(() => setTriggerValue('hovered',ticker), 500);
      });
      graph.on('plotly_unhover',() => {clearTimeout(timer);active=null;});
    });
  }
  const observer=new MutationObserver(() => bindPlotly());
  observer.observe(document.body,{subtree:true,childList:true});
  bindPlotly();
  return () => {
    clearTimeout(timer);
    observer.disconnect();
    document.removeEventListener('pointerover', onOver, true);
    document.removeEventListener('pointerout', onOut, true);
    document.removeEventListener('click',onTableSort,true);
  };
}
"""
hover_router=st.components.v2.component('rsm_ticker_hover_router',js=RSM_HOVER_JS)
hover_result=hover_router(key='rsm_hover_router_mount',on_hovered_change=lambda: None)
_hover_symbol=valid_ticker(getattr(hover_result,'hovered',None))
if _hover_symbol:
    # Trigger values are transient; re-hovering the SAME ticker must work too.
    st.session_state['_rsm_popup_request']=_hover_symbol

# Only one dialog is launched per Streamlit rerun, regardless of source.
# Avoid opening again on unrelated filter updates after a selected dataframe row.
_popup_now=valid_ticker(st.session_state.pop("_rsm_popup_request",None))
if _popup_now:
    show_ticker_popup(_popup_now)

st.divider()
st.markdown("<span class='rsm-note'>DATA SOURCES · Constituents: public S&P 500 lists · Market cap: Nasdaq snapshot via zyhe16/top-us-stock-tickers · Daily price/volume and continuous futures: Yahoo Finance via yfinance · ETF holdings: Yahoo Finance or Stock Analysis · Market breadth: derived from available constituents. No execution, no brokerage credentials, no guaranteed real-time data.</span>",unsafe_allow_html=True)
