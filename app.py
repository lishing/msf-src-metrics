import csv
import boto3
import pandas as pd
import streamlit as st
import tempfile
from st_files_connection import FilesConnection
from datetime import datetime
import matplotlib.pyplot as plt

# Main Streamlit app
def main():

    st.header('SRC Usage Metrics')

    conn = st.connection('s3', type=FilesConnection)
    
    try: 
        with st.spinner('Downloading CSV file...'):
            df = conn.read("dev-app-logging/msf-report/msf_logs_csv//output.csv", input_format="csv", ttl=60)

            # Find the earliest and latest dates in the 'Date' column
            df['Date'] = pd.to_datetime(df['Date'])
            df['Date_Only'] = df['Date'].dt.strftime('%Y-%m-%d')
            earliest_date = df['Date'].min()
            latest_date = df['Date'].max()

            selected_date_range = st.date_input(
                "Select Date Range for the report",
                (earliest_date.date(), latest_date.date()) # detault value
            )

            if selected_date_range:
                start_date, end_date = selected_date_range
                df_selected = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)]

                # metric 1: total usage
                total = df_selected["version"].count()

                # metric 2: total time saved
                time_saved = f'{round(total * 12.5 / 60)} hours'
                
                # metric 3: Usage count of this month, with MoM growth
                today = datetime.today().date()
                df_today = df[df['Date'].dt.date == today]
                current_month = today.month
                current_year = today.year
                df_this_month = df[(df['Date'].dt.month == current_month) & (df['Date'].dt.year == current_year)]
                usage_count_this_month = df_this_month.shape[0]

                # Calculate usage count for the previous month
                previous_month = current_month - 1 if current_month > 1 else 12
                previous_year = current_year if current_month > 1 else current_year - 1
                df_previous_month = df[(df['Date'].dt.month == previous_month) & (df['Date'].dt.year == previous_year)]
                usage_count_previous_month = df_previous_month.shape[0]

                # Calculate delta between current month and previous month
                delta = usage_count_this_month - usage_count_previous_month
                if usage_count_previous_month != 0:
                    percentage_delta = ((usage_count_this_month - usage_count_previous_month) / usage_count_previous_month) * 100
                else:
                    percentage_delta = 0

                # metric 4: group by assessment type and count maximum
                assessment_type_counts = df_selected['assessment_type'].value_counts()
                most_used_assessment_types = assessment_type_counts.idxmax()
                most_used_count = assessment_type_counts.max()

                # metrics column
                col1, col2, col3, col4 = st.columns(4)

                col1.metric(label = 'Total Usage to date', value=total, help = 'Data includes inputs submitted. Figures will be refreshed weekly.')
                col2.metric(label = 'Total time saved to date', value=time_saved, help='Each usage is estimated to be able to save 12.5 minutes per SA report. Based on users\' study done in Nov 2023.')
                col3.metric(label = 'Usage this month', value=usage_count_this_month, delta=delta, help='Delta is calculated based on MoM growth of the month today, not affected by time range.')
                col4.metric(label = 'Most utilized Header', value=most_used_assessment_types, help='Headers include Family, Employment, Shelter, Health, Financial Support, Food.')

                # Aggregate usage by month
                df_selected['year_month'] = df_selected['Date'].dt.to_period('M')
                usage_by_month = df_selected.groupby('year_month').size().cumsum()

                # Plot aggregate usage over time
                fig, ax = plt.subplots()
                ax.plot(usage_by_month.index.astype(str), usage_by_month.values, marker='o')
                ax.set_title('Cumulative Usage Over Time')
                ax.set_xlabel('Month')
                ax.set_ylabel('Number of generated reports')
                ax.grid(False)
                st.pyplot(fig)

                st.subheader('Raw data')
                st.dataframe(df_selected.sort_values(by='Date_Only', ascending=False), column_config={
                    "Date_Only": "Date",
                    "version": None,
                    "assessment_type": "Assessment Type",
                    "input_note": "Input",
                    "output_note": "Generated Output",
                    "year_month": None,
                },
                hide_index=True)
            
    except pd.errors.ParserError as e:
        st.error(f"Error parsing CSV file: {e}")


if __name__ == "__main__":
    main()

