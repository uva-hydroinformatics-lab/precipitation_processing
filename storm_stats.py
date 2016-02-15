# Purpose: Aggregate data from access database for given time interval (originally day)
# Authors: J. Sadler, University of Virginia
# Email: jms3fb@virginia.edu

import numpy as np
import pandas as pd
import pyodbc
import datetime
import matplotlib.pyplot as plt
import math


def get_data_frame_from_table(table_name):
    print 'getting data for {}'.format(table_name)
    # set up db connection
    MDB = "C:/Users/jeff_dsktp/Box Sync/Sadler_1stPaper/rainfall/data/rainfall_data_master.accdb"; DRV = '{Microsoft Access Driver (*.mdb, *.accdb)}'; PWD = 'pw'

    # connect to db
    con = pyodbc.connect('DRIVER={};DBQ={};PWD={}'.format(DRV,MDB,PWD))
    cur = con.cursor()

    # run a query and get the results
    SQL = 'SELECT * FROM {};'.format(table_name) # your query goes here
    rows = cur.execute(SQL).fetchall()
    a = np.array(rows)
    df = pd.DataFrame(a, columns=[i[0] for i in cur.description])
    cur.close()
    con.close()
    return df


def make_incremental(df, date_range):
    newdf = pd.DataFrame()
    non_cumulative_df = pd.DataFrame()
    for date in date_range:
        date_string = datetime.datetime.strptime(str(date), '%Y%m%d').strftime('%Y-%m-%d')
        df_date = df[date_string]
        df_date = df_date.groupby(['x', 'y'])
        for location in df_date:
            xy_df = location[1]
            cum_precip_arr = np.array(xy_df['precip_mm'])
            if cum_precip_arr[0] > 0:
                incr_precip = [cum_precip_arr[0]] #TODO: decide whether or not to keep this or make it zero to begin with
            else:
                incr_precip = [0]
            for i in range(len(cum_precip_arr)-1):
                if cum_precip_arr[i+1] >= cum_precip_arr[i]:
                    incr_precip.append(cum_precip_arr[i+1] - cum_precip_arr[i])
                else:
                    non_cumulative_df = non_cumulative_df.append(location[1].iloc[[i]])
                    incr_precip.append(cum_precip_arr[i+1])
            xy_df.loc[:, 'precip_mm'] = incr_precip
            newdf = newdf.append(xy_df)
    newdf = newdf.reset_index(inplace=False)
    non_cumulative_df.to_csv("{}.csv".format("non_cumulative"), mode='a')
    return newdf

def autolabel(ax, rects):
    # attach some text labels
    for rect in rects:
        height = rect.get_height()
        if math.isnan(height): continue
        ax.text(rect.get_x() + rect.get_width()/2., 1.05*height,
                '%d' % int(height),
                ha='center', va='bottom')

def graph_daily_totals(ax, x, y, title, ylab, xlabs):
    width = 1.
    rects = ax.bar(x, y, width)
    ax.set_ylabel(ylab)
    ax.set_xticks(x+width/2)
    ax.set_xticklabels(xlabs, rotation='vertical')
    ax.set_title(title)
    autolabel(ax, rects)

def graph_scatter(ax, df_sums, date, ylab, type):
    ax.scatter(df_sums.x, df_sums.y, c=df_sums.precip_mm, cmap='Blues', s=df_sums.precip_mm**1.3)
    for i in range(len(df_sums.x)):
        ax.annotate("{}{}".format("p",df_sums.index[i]),
                    (df_sums.x[i], df_sums.y[i]),
                    xytext=(8, 8),
                    textcoords='offset points'
                    )
    ax.set_ylabel("y[m]")
    ax.set_xlabel("x [m]")
    ax.set_title(date)

def get_daily_total(df, date):
    # return a dataframe with the sum of the rainfall at a given point for a given time span
    df_date = df[date]
    df_date = df_date.groupby(['x', 'y', 'site_name', 'src'])
    df_sums = df_date.sum()
    df_sums = df_sums.reset_index(inplace=False)
    return df_sums

def get_daily_max(df,date):
    graph_daily_totals(df_sums, date_string, "cumulative precip in mm")
    df_date = df_date.resample('15T', how={'precip_mm': 'sum'})
    df_date = df_date.reset_index(inplace=False)


hrsd_stations_in_study_area = ["MMPS-171",
                               "MMPS-185",
                               "MMPS-163",
                               "MMPS-255",
                               "MMPS-146",
                               "MMPS-004",
                               "MMPS-256",
                               "MMPS-140",
                               "MMPS-160",
                               "MMPS-144",
                               "MMPS-036",
                               "MMPS-093-2"]


date_range = [
              20130702,
              20131009,
              20140111,
              20140213,
              20140415,
              20140425,
              20140710,
              20140818,
              20140908,
              20140909,
              20140913,
              20141126,
              20141224,
              20150414,
              20150602,
              20150624,
              20150807,
              20150820,
              20150930,
              20151002
              ]

# prepare the data by pulling from the database and making the datetime the index
df = get_data_frame_from_table('vabeach_reformat_mm')
df['datetime'] = pd.to_datetime(df['datetime'])
vab_df = df.set_index('datetime')
vab_df.insert(len(vab_df.columns), 'src', 'vab')

df = get_data_frame_from_table('hrsd_obs_spatial')
df['datetime'] = pd.to_datetime(df['datetime'])
hrsd_df = df.set_index('datetime')
hrsd_df.insert(len(hrsd_df.columns), 'src', 'hrsd')

# df = get_data_frame_from_table('wu_observation_spatial')
# df['datetime'] = pandas.to_datetime(df['datetime'])
# df = df.set_index('datetime')
# inc_df = make_incremental(df, date_range)
# wu_df = inc_df.set_index('datetime')
# wu_df.insert(len(wu_df.columns), 'src', 'wu')
#
df_list = [hrsd_df, vab_df]

#combine the dfs in the list together
combined_df = pd.DataFrame()
for df in df_list:
    combined_df = combined_df.append(df)

combined_df = combined_df[(combined_df.src == "vab") | (combined_df.site_name.str.rstrip().isin(hrsd_stations_in_study_area))]
daily_tots_df = pd.DataFrame()
daily_totals = []
j = 0
fig, a = plt.subplots(2, 2, figsize=(15, 10), sharex='col', sharey = 'col')
a = a.ravel()
for i in range(len(date_range)):
    date = date_range[i]
    date = datetime.datetime.strptime(str(date), '%Y%m%d').strftime('%Y-%m-%d')
    daily_tot = get_daily_total(combined_df, date)

    #produce bar chart for day
    barX = np.arange(len(daily_tot.precip_mm))
    barY = daily_tot.precip_mm
    barX_labs = "["+ daily_tot.index.astype(str) + "] " + daily_tot.site_name +" (" + daily_tot.src + ")"
    graph_daily_totals(a[j], barX, barY, xlabs=barX_labs, title=date, ylab="precip (mm)")

    #produce scatter for the day
    graph_scatter(a[j+1], daily_tot, date, "precip (mm)", "daily total")

    #stuff to make it so there are two days per figure
    if j == 2:
        j = 0
        plt.tight_layout()
        plt.savefig('C:/Users/jeff_dsktp/Box Sync/Sadler_1stPaper/rainfall/python/storm_stats/{}_{}.png'.format("storm_summary", i/2))
        fig, a = plt.subplots(2, 2, figsize=(15, 10), sharex='col', sharey = 'col')
        a = a.ravel()
    else:
        j += 2

    #add to list of daily totals
    daily_totals.append((date, daily_tot.precip_mm.sum()))

daily_totals = zip(*daily_totals)
width = 1.
fig, ax = plt.subplots()
x = np.arange(len(daily_totals[0]))
y = daily_totals[1]
graph_daily_totals(ax, x, y, title="overall summary", xlabs=daily_totals[0], ylab="cumulative total precip (mm)")
plt.tight_layout()
plt.savefig('C:/Users/jeff_dsktp/Box Sync/Sadler_1stPaper/rainfall/python/storm_stats/{}.png'.format("summary"))
