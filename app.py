import csv
import boto3
import pandas as pd
import streamlit as st
import tempfile
from st_files_connection import FilesConnection
from datetime import datetime
import matplotlib.pyplot as plt

# import streamlit_authenticator as stauth

# from exec_summary import exec_summary as execsum

# Main Streamlit app
def main():

    st.header('SRC Usage Metrics')

    # to add a prompt for executive summary according to the last month's data. 
    # st.text('Executive summary')

    # Connect to S3
    conn = st.connection('s3', type=FilesConnection)
    
    try: 
        with st.spinner('Downloading CSV file...'):
            df = conn.read("dev-app-logging/msf-report/msf_logs_csv//output.csv", input_format="csv", ttl=60)

            # drop all rows with null value. So far those that are null are either tests, or has failed data.
            df = df.dropna(how='any',axis=0) 

            # Find the earliest and latest dates in the 'Date' column
            df['Date'] = pd.to_datetime(df['Date'])
            df['Date_Only'] = df['Date'].dt.strftime('%Y-%m-%d')
            earliest_date = df['Date'].min()
            latest_date = df['Date'].max()
            default_start_date = earliest_date
            default_end_date = latest_date

            selected_date_range = st.date_input(
                "The earlist report is from 4th Oct, 2023. If it is out of range, it will default to the earliest and latest date in the report.",
                (default_start_date.date(), default_end_date.date())  
            )

            # Filter the DataFrame based on the selected date range
            if selected_date_range:
                start_date, end_date = selected_date_range

                # Convert selected dates to pandas Timestamp for comparison
                start_date = pd.Timestamp(start_date)
                end_date = pd.Timestamp(end_date)

                # Adjust start_date if outside the range, defaulting to the closest limit
                start_date = max(min(start_date, latest_date), earliest_date)
                
                # Adjust end_date if outside the range, ensuring it's not before the start_date
                end_date = max(min(end_date, latest_date), start_date)

                # Filter the DataFrame based on the adjusted selected date range
                df_selected = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

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

                # metric 4: change to cost (based on tokens used). find average length of input and output
                # Count number of words into text
                def count_words(text):
                    words = text.split()  
                    return len(words) 

                # Calculate costs by input notes
                df['input_word_count'] = df['input_note'].fillna('').astype(str).apply(count_words)
                total_input_words = df['input_word_count'].sum()
                total_input_tokens = total_input_words / 4
                input_cost = total_input_tokens / 1000 * 0.01 # input cost for gpt-4-turbo is 0.01 for every 1000 tokens

                # have a df data which contains failed output to calculate costs better
                df_successful_output = df[df["output_note"].str.contains("Exception Raised when generating output.") == False]

                # Calculate costs by output notes
                df_successful_output['output_word_count'] = df_successful_output['output_note'].fillna('').astype(str).apply(count_words)
                total_output_words = df_successful_output['output_word_count'].sum()
                total_output_tokens = total_output_words / 4
                output_cost = total_output_tokens / 1000 * 0.03 # output cost for gpt-4-turbo is 0.03 for every 1000 tokens
                
                total_cost = round(input_cost + output_cost)

                # metrics column
                col1, col2, col3, col4 = st.columns(4)

                col1.metric(label = 'Total Usage', value=total, help = 'Data includes inputs submitted. Figures will be refreshed weekly.')
                col3.metric(label = 'Total time saved', value=time_saved, help='Each usage is estimated to be able to save 12.5 minutes per SA report. Based on users\' study done in Nov 2023.')
                col2.metric(label = 'Usage this month', value=usage_count_this_month, delta=delta, help='Delta is calculated based on MoM growth of the month today, not affected by time range.')
                col4.metric(label = 'Total cost', value=f'${total_cost}', help='Based on the costs of GPT-4 for input and output, rounded to the nearest dollar.')

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
                st.dataframe(df_selected.sort_values(by='Date_Only', ascending=False), 
                    column_config={
                    "Date_Only": "Date",
                    "assessment_type": "Assessment Type",
                    "input_note": "Input",
                    "output_note": "Generated Output",
                    "Date": None,
                    "version": None,
                    "year_month": None  
                    },
                    hide_index=True,
                    column_order=["Date_Only", "assessment_type", "input_note", "output_note"]
                    )
            
    except pd.errors.ParserError as e:
        st.error(f"Error parsing CSV file: {e}")


if __name__ == "__main__":
    main()

