"""
Loan Performance Business Dashboard
-----------------------------------
Streamlit dashboard with interactive loan performance visualizations.
Includes student and AI enhancements for clarity and interpretability.

Created on 11/29/2025
Author: Group Project Team 2
Course: ISTM 635
Last Updated : 12/01/2025
"""
#Load mports
import streamlit as st
import pandas as pd
import altair as alt


# 1. Load the Data

# Load CSV data
@st.cache_data
def load_data(file_path):
    try:
        data = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"Error: File not found at {file_path}. Ensure 'cleaned_loans.csv' is in the directory.")
        return pd.DataFrame()
    data['issue_d'] = pd.to_datetime(data['issue_d'], errors='coerce')
    data.dropna(subset=['issue_d'], inplace=True)
    return data

loan_data = load_data('cleaned_loans.csv')
if loan_data.empty:
    st.stop()


# 2. Dashboard Layout
# Create dashboard layout and title
st.set_page_config(layout="wide", page_title="Loan Performance Dashboard")
st.title("💰 Loan Performance Business Dashboard")
st.markdown("Interactive analysis of loan issuance and risk profiles.")


# 3. Sidebar Filters (Global)

st.sidebar.header("User Configuration & Filters")

# Grade filter - AI ENHANCEMENT
all_grades = sorted(loan_data['grade'].dropna().unique().tolist())
selected_grade = st.sidebar.multiselect("Select Loan Grade(s):", options=all_grades, default=all_grades)

# Home ownership filter - HUMAN ENHANCEMENT
all_ownerships = loan_data['home_ownership'].dropna().unique().tolist()
selected_ownership = st.sidebar.multiselect("Select Home Ownership Status(es):", options=all_ownerships, default=all_ownerships)

# Loan purpose filter
all_purposes = sorted(loan_data['purpose'].dropna().unique().tolist())
selected_purposes = st.sidebar.multiselect("Filter by Loan Purpose:", options=all_purposes, default=all_purposes)

# Metric toggle - HUMAN ENHANCEMENT
metric_toggle = st.sidebar.toggle("Toggle Metric: Sum vs Average Loan Amount", value=True)
metric_aggregation = 'sum' if metric_toggle else 'mean'
metric_label = 'Total Loan Amount' if metric_toggle else 'Average Loan Amount'

# Top N states filter - AI ENHANCEMENT
top_n_states = st.sidebar.radio("Limit States to:", [10, 20, "All"])

# Global loan amount range filter - HUMAN ENHANCEMENT
min_amt, max_amt = int(loan_data['loan_amnt'].min()), int(loan_data['loan_amnt'].max())
amt_range = st.sidebar.slider(
    "Select Loan Amount Range:",
    min_amt,
    max_amt,
    (min_amt, max_amt),
    key="global_loan_range"
)

# Pie chart percentage toggle - HUMAN ENHANCEMENT
show_percent = st.sidebar.checkbox("Show Pie Chart as Percentages", value=False)

# Apply global filters
filtered_data = loan_data[
    (loan_data['grade'].isin(selected_grade)) &
    (loan_data['home_ownership'].isin(selected_ownership)) &
    (loan_data['purpose'].isin(selected_purposes)) &
    (loan_data['loan_amnt'] >= amt_range[0]) &
    (loan_data['loan_amnt'] <= amt_range[1])
].copy()

# Apply state restriction globally
if top_n_states != "All":
    state_totals = filtered_data.groupby('addr_state').size().sort_values(ascending=False)
    top_states = state_totals.head(int(top_n_states)).index.tolist()
    filtered_data = filtered_data[filtered_data['addr_state'].isin(top_states)]



# 4. Visualizations


#  Visualization 1: Purpose Bar Chart  
#  Create bar chart that shows loan amount by purpose
def create_purpose_bar_chart(df, agg_type, agg_label):
    st.header("1. Loan Amount by Purpose")
    chart_data = df.groupby('purpose')['loan_amnt'].agg(agg_type).reset_index()
    chart_data.columns = ['purpose', agg_label]
    # AI ENHANCEMENT - BLUE SHADING
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X(agg_label, title=agg_label),
        y=alt.Y('purpose', sort='-x'),
        tooltip=['purpose', alt.Tooltip(agg_label, format=',.0f')],
        color=alt.Color(agg_label, scale=alt.Scale(scheme='blues'))
    ).properties(title=f'{agg_label} by Loan Purpose')
    st.altair_chart(chart, use_container_width=True)

#  Visualization 2: Loan Amount Distribution by Grade 
#  Create box plot that shows loan amount distribution by grade
def create_box_plot(df):
    st.header("2. Loan Amount Distribution by Grade")
    counts = df.groupby('grade').size().reset_index(name='n')
    counts['label'] = counts.apply(lambda row: f"n={row['n']}", axis=1)

    box = alt.Chart(df).mark_boxplot(extent='min-max').encode(
        x=alt.X('grade:N', title='Loan Grade'),
        y=alt.Y('loan_amnt:Q', title='Loan Amount'),
        tooltip=['grade', 'loan_amnt']
    )
    # AI ENHANCEMENT - SAMPLE SIZES
    labels = alt.Chart(counts).mark_text(
        dy=20,
        fontSize=12,
        fontWeight='bold',
        color='darkblue'
    ).encode(
        x='grade:N',
        y=alt.value(0),
        text='label:N'
    )

    chart = box + labels
    st.altair_chart(chart, use_container_width=True)

#  Visualization 3: Status Pie Chart 
#  Create pie chart that shows distribution of loan status
def create_status_pie_chart(df, show_percent):
    st.header("3. Distribution of Loan Status")
    status_counts = df['loan_status'].value_counts().reset_index()
    status_counts.columns = ['loan_status', 'count']
    status_counts['share'] = status_counts['count'] / status_counts['count'].sum()

    theta_field = "share" if show_percent else "count"
    tooltip_fields = ["loan_status", alt.Tooltip(theta_field, format=".1%" if show_percent else ",")]
    # AI ENHANCEMENT - LEGEND SELECT
    legend_select = alt.selection_single(fields=['loan_status'], bind='legend')

    base = alt.Chart(status_counts).encode(
        theta=alt.Theta(theta_field, stack=True),
        color=alt.condition(
            legend_select,
            alt.Color('loan_status:N', title='Loan Status'),
            alt.value('lightgray')
        ),
        tooltip=tooltip_fields
    )

    pie = base.mark_arc(outerRadius=120)
    text = base.mark_text(radius=140).encode(text=alt.condition(legend_select, 'loan_status', alt.value('')))

    chart = pie + text
    st.altair_chart(chart.add_selection(legend_select), use_container_width=True)

#  Visualization 4: Loan Counts by State & Grade 
#  Create heat map that shows loan counts by state and grade
def create_state_grade_treemap(df):
    st.header("4. Loan Counts by State & Grade (Treemap)")
    df = df.dropna(subset=['addr_state', 'grade'])
    state_counts = df.groupby(['addr_state', 'grade']).size().reset_index(name='count')
    totals = state_counts.groupby('addr_state')['count'].sum().sort_values(ascending=False)
    state_order = totals.index.tolist()
    chart = alt.Chart(state_counts).mark_rect().encode(
        x=alt.X('addr_state:N', title='State', sort=state_order),
        y=alt.Y('grade:N', title='Grade'),
        size='count:Q',
        color=alt.Color('count:Q', scale=alt.Scale(scheme='inferno'), title='Loan Count'),
        tooltip=['addr_state', 'grade', 'count']
    ).properties(title='Treemap of Loan Counts by State & Grade')
    st.altair_chart(chart, use_container_width=True)


# 5. Layout
# Run visualizations
col1, col2 = st.columns(2)
with col1:
    create_purpose_bar_chart(filtered_data, metric_aggregation, metric_label)
    st.markdown("---")
    create_status_pie_chart(filtered_data, show_percent)
with col2:
    create_box_plot(filtered_data)
    st.markdown("---")
    create_state_grade_treemap(filtered_data)


# 6. Completion Message
# Provide completion message
st.success("Dashboard generation complete. Use the sidebar filters to interact with the data.")