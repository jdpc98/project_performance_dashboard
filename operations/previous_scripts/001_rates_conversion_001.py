import pandas as pd
import os
from datetime import datetime
from openpyxl import load_workbook
import tkinter as tk
from tkinter import filedialog
import warnings

#i set the file path 
rate_file_path = r"C:\Users\jose.pineda\Desktop\operations\RATES.xlsx"

#i read the excel file
df_rates = pd.read_excel(rate_file_path, sheet_name='Rates', header=None)
print(df_rates)
#i define func to take trm values 
def trm_ingestion(rates_df):
    df_rates= rates_df.copy()
    # Extract arrays separately
    trm_values = df_rates.iloc[0, 4:29].values
    bogota_vals = df_rates.iloc[1, 4:29].values
    houston_vals = df_rates.iloc[2, 4:29].values

    # now i get the dates 
    df_dates = df_rates.iloc[4:6, 4:29].copy()
    #i forward fill the df_dates 
    df_dates.ffill(axis=1, inplace=True)
    # i create a new row below 
    df_dates.loc[6] = 0

    # Combine the year and month values into a new dates row
    df_dates.loc['concat'] = df_dates.loc[4].astype(str) + df_dates.loc[5].astype(str)

    # Extract the concatenated dates row by label instead of integer index
    dates_vals = df_dates.loc['concat'].values
    # Combine them into a DataFrame
    df_trm = pd.DataFrame({
        "TRM": trm_values,
        "Bogota_val": bogota_vals,
        "Houston_val": houston_vals,
        "Dates": dates_vals
    })

    print(df_trm.head())
    return df_trm
#i run trm ingesting func to get values
df_trm_vals = trm_ingestion(df_rates)

#i define func to take rates per date
def rates_ingestion(rates_df):
    df_rates = rates_df.copy()
    #i drop all rows from 1 to 7, so 0:6
    df_rates = df_rates.drop(df_rates.index[0:7])
    #i drop all columns from column 29 onwards
    df_rates = df_rates.drop(df_rates.columns[29:], axis=1)
    
    print(df_rates)
    
        # now i get the dates 
    
    df_dates = rates_df.iloc[4:6, 4:29].copy()
    #i forward fill the df_dates 
    df_dates.ffill(axis=1, inplace=True)
    # i create a new row below 
    df_dates.loc[6] = 0

    # Combine the year and month values into a new dates row
    df_dates.loc['concat_cont'] = df_dates.loc[4].astype(str) + df_dates.loc[5].astype(str)
    #i create 4 new columns at the beginning, in order: "ID#", "Personel", "2022Whole_Year", "2023Whole_Year"
    df_dates.insert(0, "ID#", "ID#")
    df_dates.insert(1, "Employee", "Employee")
    df_dates.insert(2, "2022Whole_Year", "2022Whole_Year")
    df_dates.insert(3, "2023Whole_Year", "2023Whole_Year")
    #print(df_dates)
    
        # Extract the concatenated dates row by label instead of integer index
    dates_vals = df_dates.loc['concat_cont'].values
    print(dates_vals)
    #make the values in dates_vals the index of  df_rates
    df_rates.columns = dates_vals
    print(df_rates)
    return df_rates

#i run func to get values
rates_ingestion(df_rates)
df_actual_rates=rates_ingestion(df_rates)

def load_coef(rates_df): 
   #i get the coef value
    coef = rates_df.iloc[0, 32]
    print(coef)
    return coef
    
loaded_c=load_coef(df_rates)

def loaded_rates_ingestion(rates_df):
    lr_df = rates_df.copy()
    #i drop all rows from 1 to 4, so 0:3
    lr_df = lr_df.drop(lr_df.index[0:4])
    #i drop columns from C to AC
    lr_df = lr_df.drop(lr_df.columns[2:29], axis=1)
    #rename index
    lr_df.index = range(len(lr_df))
    
    #i drop row 6
    lr_df = lr_df.drop(lr_df.index[2])
    #rename index
    lr_df.index = range(len(lr_df))
    #drop row 0
    lr_df = lr_df.drop(lr_df.index[0])
    #rename index
    lr_df.index = range(len(lr_df))
    #rename columns
    lr_df.columns = ["ID#", "Employee", "RAW_USD", "LOADED_USD", "LOADED_COP", "RAW_COP"]
    #i drop the row 0
    lr_df = lr_df.drop(lr_df.index[0])
     #rename index
    lr_df.index = range(len(lr_df))
    
    
    
    print(lr_df)
    return lr_df


    

loaded_rates=loaded_rates_ingestion(df_rates)