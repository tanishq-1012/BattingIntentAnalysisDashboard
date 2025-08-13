import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from math import ceil

# --------------------------
# Page Setup
# --------------------------
st.set_page_config(page_title="🏏 Batting Intent Analysis Dashboard", layout="wide")
st.title("🏏 Batting Intent Analysis – IPL Match 1473461")
st.markdown("Explore batting performance across match phases in an interactive format.")

# --------------------------
# File Upload
# --------------------------
uploaded_file = st.file_uploader("Upload Deliveries CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df_copy = df.copy()

    # --------------------------
    # Data Preprocessing
    # --------------------------
    def get_phase(over):
        if over < 6:
            return 'Powerplay'
        elif 6 <= over < 15:
            return 'Middle Overs'
        else:
            return 'Death Overs'

    df_copy['phase'] = df_copy['over'].apply(get_phase)
    df_copy['batting_team'] = df_copy['team']
    df_copy['ball_outcome'] = df_copy['runs_batter'].apply(
        lambda x: 'Dot' if x == 0 else ('Boundary' if x >= 4 else 'Run')
    )

    # Sidebar Filters
    st.sidebar.header("Filters")
    selected_phase = st.sidebar.multiselect(
        "Select Match Phases", options=df_copy['phase'].unique(), default=df_copy['phase'].unique()
    )
    selected_team = st.sidebar.multiselect(
        "Select Teams", options=df_copy['batting_team'].unique(), default=df_copy['batting_team'].unique()
    )

    df_filtered = df_copy[df_copy['phase'].isin(selected_phase) & df_copy['batting_team'].isin(selected_team)]

    # --------------------------
    # Create Tabs (Slides)
    # --------------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Strike Rate by Phase",
        "🏏 Team-wise Intent",
        "🎯 Boundary vs Dot %",
        "📉 Runs vs Wickets",
        "🔘 Radar Chart"
    ])

    # --- Tab 1: Strike Rate by Batter ---
    with tab1:
        batting_intent = (
            df_filtered.groupby(['batter', 'phase'])
            .agg(balls_faced=('runs_batter', 'count'), total_runs=('runs_batter', 'sum'))
            .reset_index()
        )
        batting_intent['strike_rate'] = (batting_intent['total_runs'] / batting_intent['balls_faced']) * 100
        batting_intent = batting_intent[batting_intent['balls_faced'] >= 5]

        fig1 = px.bar(
            batting_intent, x='batter', y='strike_rate', color='phase',
            barmode='group', title='📊 Strike Rate by Batter Across Phases',
            hover_data={'balls_faced': True, 'total_runs': True, 'strike_rate': ':.2f'}
        )
        st.plotly_chart(fig1, use_container_width=True)

    # --- Tab 2: Team-wise Intent ---
    with tab2:
        team_phase_intent = (
            df_filtered.groupby(['batting_team', 'phase'])
            .agg(balls_faced=('runs_batter', 'count'), total_runs=('runs_batter', 'sum'))
            .reset_index()
        )
        team_phase_intent['strike_rate'] = (team_phase_intent['total_runs'] / team_phase_intent['balls_faced']) * 100

        fig2 = px.bar(
            team_phase_intent, x='phase', y='strike_rate', color='batting_team',
            barmode='group', title='🏏 Team-wise Batting Intent by Phase'
        )
        st.plotly_chart(fig2, use_container_width=True)

    # --- Tab 3: Boundary % vs Dot % ---
    with tab3:
        batter_outcome_stats = (
            df_filtered.groupby('batter')
            .ball_outcome.value_counts(normalize=True)
            .unstack().fillna(0) * 100
        ).reset_index()

        balls_faced = df_filtered.groupby('batter').size().reset_index(name='balls_faced')
        batter_outcome_stats = batter_outcome_stats.merge(balls_faced, on='batter')
        batter_outcome_stats = batter_outcome_stats[batter_outcome_stats['balls_faced'] >= 10]

        fig3 = go.Figure([
            go.Bar(x=batter_outcome_stats['batter'], y=batter_outcome_stats['Boundary'], name='Boundary %', marker_color='green'),
            go.Bar(x=batter_outcome_stats['batter'], y=batter_outcome_stats['Dot'], name='Dot Ball %', marker_color='red')
        ])
        fig3.update_layout(title='🎯 Boundary % vs Dot Ball %', barmode='group', xaxis_tickangle=-45)
        st.plotly_chart(fig3, use_container_width=True)

    # --- Tab 4: Runs vs Wickets ---
    with tab4:
        wickets_df = df_filtered[df_filtered['player_out'].notna()]
        wickets_by_over = wickets_df.groupby('over').size().reset_index(name='wickets')
        runs_by_over = df_filtered.groupby('over')['runs_batter'].sum().reset_index(name='total_runs')

        overwise_analysis = pd.merge(runs_by_over, wickets_by_over, on='over', how='left').fillna(0)

        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=overwise_analysis['over'], y=overwise_analysis['total_runs'], name='Runs Scored', marker_color='skyblue'))
        fig4.add_trace(go.Scatter(x=overwise_analysis['over'], y=overwise_analysis['wickets'], name='Wickets',
                                   mode='lines+markers', marker=dict(color='red', size=8), yaxis='y2'))
        fig4.update_layout(
            title='📉 Over-wise Runs vs Wickets',
            yaxis=dict(title='Runs'),
            yaxis2=dict(title='Wickets', overlaying='y', side='right')
        )
        st.plotly_chart(fig4, use_container_width=True)

    # --- Tab 5: Radar Chart ---
    with tab5:
        batter_stats = (
            df_filtered.groupby('batter')
            .agg(balls_faced=('runs_batter', 'count'), total_runs=('runs_batter', 'sum'),
                 dismissals=('player_out', lambda x: x.notna().sum()))
            .reset_index()
        )

        outcome_counts = df_filtered.groupby(['batter', 'ball_outcome']).size().unstack().fillna(0)
        outcome_counts['dot_percent'] = (outcome_counts['Dot'] / outcome_counts.sum(axis=1)) * 100
        outcome_counts['boundary_percent'] = (outcome_counts['Boundary'] / outcome_counts.sum(axis=1)) * 100
        outcome_counts = outcome_counts[['dot_percent', 'boundary_percent']].reset_index()

        batter_profiles = pd.merge(batter_stats, outcome_counts, on='batter')
        batter_profiles['strike_rate'] = (batter_profiles['total_runs'] / batter_profiles['balls_faced']) * 100
        batter_profiles['average'] = batter_profiles.apply(
            lambda row: row['total_runs'] / row['dismissals'] if row['dismissals'] > 0 else float('inf'), axis=1
        )
        batter_profiles = batter_profiles[batter_profiles['balls_faced'] >= 10]

        top_batters_radar = batter_profiles.sort_values(by='strike_rate', ascending=False).head(4)
        metrics = ['strike_rate', 'dot_percent', 'boundary_percent']
        normalized_profiles = top_batters_radar[['batter'] + metrics].copy()

        for metric in metrics:
            max_val = batter_profiles[metric].max()
            normalized_profiles[metric] = (normalized_profiles[metric] / max_val) * 100

        fig5 = go.Figure()
        for _, row in normalized_profiles.iterrows():
            r = row[metrics].tolist() + [row[metrics[0]]]
            theta = metrics + [metrics[0]]
            fig5.add_trace(go.Scatterpolar(r=r, theta=theta, fill='toself', name=row['batter']))
        fig5.update_layout(title='🔘 Top Batters Radar Chart', polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
        st.plotly_chart(fig5, use_container_width=True)

else:
    st.warning("Please upload the match deliveries CSV to start analysis.")
