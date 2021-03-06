# Purpose: Aggregate data from access database for given time interval (originally day)
# Authors: J. Sadler, University of Virginia
# Email: jms3fb@virginia.edu

import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import math
import os
import matplotlib.animation as animation
from descartes import PolygonPatch
import shapefile
import sqlite3

basedir = os.path.dirname(__file__)
data_dir = os.path.join(basedir, '../Data/')
db_filename = os.path.join(data_dir, 'master.sqlite')

# plt.rcParams['animation.ffmpeg_path'] = 'C:/Users/jeff_dsktp/Downloads/ffmpeg-20160301-git-1c7e2cf-win64-static/ffmpeg-20160301-git-1c7e2cf-win64-static/bin/ffmpeg'

####################################################################################################
# Data preparation functions #######################################################################
####################################################################################################


def get_data_frame_from_table(table_name):
    print 'fetching data from database for {}'.format(table_name)
    # set up db connection
    global basedir

    # connect to db
    con = sqlite3.connect(db_filename)

    # run a query and get the results
    sql = 'SELECT * FROM {};'.format(table_name)  # your query goes here
    df = pd.read_sql(sql, con)
    con.close()
    return df


def make_incremental(df, date_range):
    newdf = pd.DataFrame()
    non_cumulative_df = pd.DataFrame()
    for date in date_range:
        print "making incremental for {}".format(date)
        df_date = df[date]
        df_date = df_date.groupby(['x', 'y'])
        for location in df_date:
            xy_df = location[1]
            cum_precip_arr = np.array(xy_df['precip_mm'])
            incr_precip = [0]
            for i in range(len(cum_precip_arr)-1):
                if cum_precip_arr[i+1] >= cum_precip_arr[i] > 0:
                    incr_precip.append(cum_precip_arr[i+1] - cum_precip_arr[i])
                else:
                    non_cumulative_df = non_cumulative_df.append(location[1].iloc[[i]])
                    incr_precip.append(0)
            xy_df.loc[:, 'precip_mm'] = incr_precip
            newdf = newdf.append(xy_df)
    newdf = newdf.reset_index(inplace=False)
    non_cumulative_df.to_csv("{}.csv".format("non_cumulative"), mode='a')
    return newdf


def combine_data_frames(exclude_zeros=True):
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

    # prepare the data by pulling from the database and making the datetime the index
    df = get_data_frame_from_table('all_data')
    df['datetime'] = pd.to_datetime(df['datetime'])
    if exclude_zeros:
        df = zero_sum_days_to_nan(df)
    df = df.set_index('datetime')

    return df


def get_date_range():
    dr = [
                  20130702,  # dst
                  20131009,  # dst
                  20140111,  # no dst
                  20140213,  # no dst
                  20140415,  # dst
                  20140425,  # dst
                  20140710,  # dst
                  20140818,  # dst
                  20140908,  # dst
                  20140909,  # dst
                  20140913,  # dst
                  20141126,  # no dst
                  20141224,  # no dst
                  20150414,  # dst
                  20150602,  # dst
                  20150624,  # dst
                  20150807,  # dst
                  20150820,  # dst
                  20150930,  # dst
                  20151002   # dst
                  ]

    dr = reformat_dates(dr)
    return dr


def get_outline_polygon():
    # read in shapefile for city outline
    d = "../../Data/GIS/vab_boundary_prj_m.shp"
    ps = shapefile.Reader(d)
    outline_poly = ps.iterShapes().next().__geo_interface__

    t = ()
    for i in range(len(outline_poly['coordinates'][0])):
        if outline_poly is not None:
            t += ((outline_poly['coordinates'][0][i][0]/1000,
                   outline_poly['coordinates'][0][i][1]/1000),)
    t = t,
    outline_poly['coordinates'] = t
    return outline_poly


def read_sub_daily(table_name):
    """
    :param table_name: should be one of three in the database 'fif', 'hr', 'daily'
    :return:
    """
    sd = get_data_frame_from_table(table_name)
    sd.set_index('site_name', inplace=True)
    return sd


def qc_wu(df):
    df = df.reset_index()
    bad_sites = ['KVAVIRGI52', 'KVAVIRGI112', 'KVAVIRGI126', 'KVAVIRGI129', 'KVAVIRGI117',
                 'KVAVIRGI122', 'KVAVIRGI147', 'KVAVIRGI137']
    for bs in bad_sites:
        df = df[df['site_name'] != bs]
    df = df.set_index('site_name')
    return df


####################################################################################################
# Plotting functions ###############################################################################
####################################################################################################


def autolabel(ax, rects):
    # attach some text labels
    for rect in rects:
        height = rect.get_height()
        if math.isnan(height):
            continue
        ax.text(rect.get_x() + rect.get_width()/2., 1+height,
                '%d' % int(height),
                ha='center',
                va='bottom',
                fontsize=9)


def graph_bars(ax, x, y, **kwargs):
    k = kwargs
    print ("graphing bars for {}".format(k['title']))
    rects = ax.bar(x, y, k['width'], color=k['color'])
    ax.set_ylabel(k.get('ylab'), fontsize=kwargs.get('font_size'), multialignment='center')
    ax.set_xticks(x+k['width']/2)
    ax.set_xticklabels(k.get('xlabs'), rotation='vertical', fontsize=kwargs.get('font_size'))
    ax.set_title(k['title'])
    ax.tick_params(labelsize=kwargs.get('font_size'))
    # autolabel(ax, rects)
    return rects


def plot_sum_by_station_bars(summ_df, f_dir, flav):
    ply = get_outline_polygon()
    fig, ax = plt.subplots(1, 2, figsize=(10, 6))

    # bars for overall sum by station##
    sum_by_station = summ_df.iloc[:, 3:].mean(axis=1)
    barX = np.arange(len(sum_by_station))
    graph_bars(ax[0],
               barX,
               sum_by_station,
               title="",
               xlabs=sum_by_station.index,
               ylab="precip (mm)",
               width=1,
               color='b',
               font_size=2)

    # scatter for overall sum by station ##
    graph_scatter(ax[1],
                  summ_df.x/1000,
                  summ_df.y/1000,
                  summ_df.index,
                  title="",
                  scale=sum_by_station,
                  c_limits=(sum_by_station.min(),
                            sum_by_station.max()),
                  marker_scale=2.6,
                  ply=ply,
                  label=True)
    fig.suptitle("Summary by station")
    plt.tight_layout()
    plt.savefig("{}{}_{}.png".format(check_dir(f_dir), "overall_summary_by_station", flav), dpi=500)


def plot_sum_by_day(summ_df, filename):
    fig, ax = plt.subplots(figsize=(5, 2.8))
    daily_totals = summ_df.iloc[:, 3:].mean()
    daily_std = summ_df.iloc[:, 3:].std()
    x = np.arange(len(daily_totals)*2, step=2)
    y = daily_totals
    width = 0.75
    ft_size = 9
    r1 = graph_bars(ax,
                    x,
                    y,
                    title="",
                    xlabs=daily_totals.index,
                    ylab="Average Total Rainfall \n (mm)",
                    width=width,
                    font_size=ft_size,
                    color='b')
    r2 = graph_bars(ax,
                    x+width,
                    daily_std,
                    title="",
                    xlabs=daily_totals.index,
                    ylab="Average Total Rainfall \n (mm)",
                    font_size=ft_size,
                    width=width,
                    color='y')
    ax.set_ylim(top=daily_totals.max()*1.1)
    ax.legend((r1[0], r2[0]), ("Depth", "St. Dev"), ncol=2, fontsize=ft_size)
    fig.tight_layout()
    plt.savefig(filename, dpi=300)


def graph_scatter(ax, x, y, sites, title, scale, c_limits, marker_scale, label, **kwargs):
    ply = get_outline_polygon()
    ax.add_patch(PolygonPatch(ply, fc='lightgrey', ec='grey', alpha=0.3))
    ax.axis([3700, 3730, 1050, 1070])
    print ("graphing scatter for {}".format(title))
    sc = ax.scatter(x,
                    y,
                    c=scale,
                    cmap='Blues',
                    s=scale*marker_scale+1,
                    vmin=c_limits[0],
                    vmax=c_limits[1],
                    linewidth=0.5,
                    alpha=0.85)
    if label:
        for i in range(len(x)):
            ax.annotate(sites[i],
                        (x[i], y[i]),
                        xytext=(1, 1),
                        textcoords='offset points',
                        fontsize=2
                        )
    title = title.split(" ")[-1] if ":" in title else title
    ax.set_title(title, fontsize=kwargs.get('font_size'), weight="bold")
    ax.tick_params(labelsize=kwargs.get('font_size'))
    ax.locator_params(nbins=2)
    return sc


def plot_scatter_subplots(df, **kwargs):
    """
    :param df: data frame to plot with site_name as index. must include x and y attributes.
    data starts from column
     index 3
    :param kwargs: necessary kwargs: title, marker_scale, label(bool), title, units, dty (save
     directory), and type
    :return:void
    """
    k = kwargs
    font_size = 9
    num_cols = len(df.columns[3:])
    if num_cols < 2:
        fig, a = plt.subplots(1, figsize=(6, 4.2), sharex=True, sharey=True)
        a = [a]
    elif num_cols < 20:
        rows = int(math.ceil(num_cols/4.))
        fig, a = plt.subplots(rows, 4, sharex=True, sharey=True, figsize=(6.5, rows*1.4))
        a = a.ravel()
    else:
        fig, a = plt.subplots(5, 4, sharex=True, sharey=True, figsize=(6.5, 6.5))
        a = a.ravel()
    for ax in a:
        ax.tick_params(labelsize=8)
        ax.locator_params(nbins=5)

    # scatter subplots for all days
    c_limits = k.get('c_limits', (df.iloc[:, 3:].min().min(), df.iloc[:, 3:].max().max()))
    i = 0
    for col in df.columns[3:]:
        # check if value is below a certain level in mm, leave it out
        d = df[df[col] > k['threshold']]

        sc = graph_scatter(a[i],
                           d.x/1000,
                           d.y/1000,
                           d.index,
                           col,
                           d[col],
                           c_limits,
                           k['marker_scale'],
                           k.get('label', False),
                           font_size=font_size)
        i += 1
    cax = fig.add_axes([0.815, 0.1, 0.025, 0.8])
    cb = fig.colorbar(sc, cax=cax)
    cb.set_label(k['units'], fontsize=font_size)
    fig.text(0.005, .5, "y [km]", rotation="vertical", fontsize=font_size, va='center')
    fig.text(0.48, 0.03, "x [km]", fontsize=font_size, ha='right')
    if ":" in col:
        fig.suptitle(col.split(" ")[0], fontsize=font_size, weight='bold', ha='right')
        fig.subplots_adjust(top=.83, bottom=0.15)
    fig.tight_layout()
    plt.tick_params(labelsize=font_size)
    plt.subplots_adjust(wspace=0.25, hspace=.3, right=0.8)
    plt.savefig(k['filename'], dpi=400)
    return fig, a


def plot_subdaily_scatter(df_list, create_ani, t_step, **kwargs):
    # get number of 20 subplot figures we need
    dty = kwargs['dty']
    dty += "subdaily/{}/".format(t_step)
    for d in df_list:
        date = d[0]
        df = d[1]
        n_subplots_per_fig = 20
        startcol = 3

        num_obs = len(df.columns[startcol:])
        num_figs = num_obs/n_subplots_per_fig

        date_dir = "{}{}/".format(dty, date)

        if create_ani:
            create_animation(df, date_dir)

        clims = (df.iloc[:, 3:].min().min(), df.iloc[:, 3:].max().max())

        # plot 20 sublots at a time
        for i in range(num_figs):
            plot_df = df.iloc[:, :startcol]
            scol = startcol+n_subplots_per_fig*i
            ecol = startcol+n_subplots_per_fig+n_subplots_per_fig*i
            p = plot_df.join(df.iloc[:, scol:ecol])
            t0 = p.columns[startcol].replace(":", ".")
            t1 = p.columns[n_subplots_per_fig+startcol-1].replace(":", ".")
            title = "{} - {}".format(t0, t1)
            kwargs['title'] = title
            kwargs['c_limits'] = clims
            kwargs['dty'] = date_dir
            plot_scatter_subplots(p,
                                  **kwargs)

        # add last storms (those above the last divisible by 20 storms)
        if num_obs % 20 != 0:
            plot_df = df.iloc[:, :startcol]
            scol = startcol+n_subplots_per_fig*num_figs
            p = plot_df.join(df.iloc[:, scol:])
            t0 = p.columns[startcol].replace(":", ".")
            t1 = p.columns[-1].replace(":", ".")
            title = "{} - {}".format(t0, t1)
            kwargs['c_limits'] = clims
            kwargs['title'] = title
            kwargs['dty'] = date_dir
            plot_scatter_subplots(p,
                                  **kwargs)


def create_animation(df, dty):
    # set up writer
    ply = get_outline_polygon()
    Writer = animation.FFMpegWriter()

    # set up figure
    startcol = 3
    num_obs = len(df.columns[startcol:])
    fig = plt.figure()
    ax = plt.gca()
    ax.add_patch(PolygonPatch(ply, fc='lightgrey', ec='grey', alpha=0.3))
    ax.axis([3700, 3730, 1050, 1070])
    clims = (df.iloc[:, 3:].min().min(), df.iloc[:, 3:].max().max())
    l = []

    # create animation panels
    for i in range(num_obs):
        scale = df.iloc[:, startcol+i]
        marker_scale = 12
        p = plt.scatter(df.x/1000,
                        df.y/1000,
                        c=scale,
                        cmap='Blues',
                        s=scale*marker_scale+1,
                        vmin=clims[0],
                        vmax=clims[1])

        date_and_time = df.columns[i+3]
        space_loc = date_and_time.find(' ')
        d = date_and_time[:space_loc]
        t = date_and_time[space_loc+1:]
        s = plt.text(3725, 1067, t)
        plt.title(d)
        if i == num_obs-1:
            plt.ylabel("y[km]")
            plt.xlabel("x[km]")
            plt.colorbar(p)
        l.append([p, s])

    ani = animation.ArtistAnimation(fig, l, blit=True)
    ani.save('{}{}_animation.mp4'.format(check_dir(dty), d), writer=Writer)
    # plt.show()


####################################################################################################
# Data aggregation type functions ##################################################################
####################################################################################################
def get_empty_summary_df():
    # create an empty df with just the site_names, xs, ys, and srcs to fill in the summary data
    empty_daily_tots_df = get_data_frame_from_table('sites_list')
    empty_daily_tots_df = empty_daily_tots_df.set_index('site_name')
    empty_daily_tots_df['x'] = pd.to_numeric(empty_daily_tots_df['x'])
    empty_daily_tots_df['y'] = pd.to_numeric(empty_daily_tots_df['y'])
    return empty_daily_tots_df


def get_daily_aggregate(df, date, time_step):
    # return a dataframe with the sum of the rainfall at a given point for a given time span
    df = df[date]
    df_gp = df.groupby(['x', 'y', 'site_name', 'src'])
    df_agg = df_gp.resample(time_step).agg({'precip_mm': np.sum})
    return df_agg


def get_daily_tots_df(exclude_zeros=True, qc=True):
        summary_df = get_empty_summary_df()
        df = combine_data_frames(exclude_zeros=exclude_zeros)
        for date in get_date_range():
            daily_tot = get_daily_aggregate(df, date, "D")
            daily_tot = daily_tot.sum(level="site_name")

            # add to summary dataframe
            daily_tot.rename(columns={'precip_mm': date}, inplace=True)
            summary_df = summary_df.join(daily_tot[date])
        if qc:
            return qc_wu(summary_df)
        else:
            return summary_df


def get_subdaily_df(time_step, exclude_zeros=True):
    date_range = get_date_range()
    df = combine_data_frames(exclude_zeros)
    dur_df = get_storm_durations(df, date_range, 0.025)
    summary_df = get_empty_summary_df()
    l = []
    for date in date_range:
        sdf = summary_df
        print "getting subdaily values for {}".format(date)
        df_date = df[date]

        # get duration
        e = dur_df["end_time"][date]
        s = dur_df["start_time"][date]
        if time_step == "H":
            s = s - pd.Timedelta(minutes=s.minute)
        time_range = pd.date_range(s, e, freq=time_step)
        time_range_formatted = []
        for t in time_range:
            time_range_formatted.append(t._repr_base)

        # aggregate
        df_gp = df_date.groupby(['x', 'y', 'site_name', 'src'])
        df_agg = df_gp.resample(time_step).agg({'precip_mm': np.sum})
        df_agg = df_agg.reset_index()
        df_agg = df_agg.set_index("datetime")

        # sum for each time step in duration
        for time in time_range_formatted:
            t = get_daily_aggregate(df_agg, time, time_step)
            t = t.sum(level="site_name")

            # add to summary dataframe
            t.rename(columns={'precip_mm': time}, inplace=True)
            sdf = sdf.join(t[time])
        l.append((date, sdf))
    return l


def combine_sub_daily_dfs(df_list):
    summ_df = get_empty_summary_df()
    for df in df_list:
        summ_df = summ_df.join(df[1].ix[:, 3:])
    a = summ_df.iloc[:, 3:].sum()
    a = a[a > 0]
    cols = ['x', 'y', 'src']
    cols.extend(a.index)
    summ_df = summ_df.loc[:, cols]
    summ_df = qc_wu(summ_df)
    return summ_df


def get_storm_durations(df, date_range, trim_percent):
    i = 0
    for date in date_range:
        df_agg = get_daily_aggregate(df, date, "15T")
        time_sums = df_agg.sum(level="datetime")
        cum_percent = time_sums.cumsum()/time_sums.sum()
        trimmed_indices = \
            cum_percent[(cum_percent['precip_mm'] > trim_percent) &
                        (cum_percent['precip_mm'] < (1-trim_percent))].index
        start_time = trimmed_indices.min()
        end_time = trimmed_indices.max()
        duration = (end_time-start_time).total_seconds()/3600
        if i == 0:
            dur_df = pd.DataFrame({'start_time': [start_time], 'end_time':[end_time],
                                   'date': [date], 'duration (hr)': [duration]})
        else:
            dur_df = dur_df.append({'start_time': start_time, 'end_time':end_time, 'date': date,
                                    'duration (hr)': duration}, ignore_index=True)
        i=1
    dur_df = dur_df.set_index("date")
    return dur_df


def get_daily_max_intensities(df, date_range, time_step):
    summary_df = get_empty_summary_df()
    for date in date_range:
        df_agg = get_daily_aggregate(df, date, "15T")
        if time_step == 'H':
            df_agg = pd.rolling_sum(df_agg, 4).max(level='site_name')
        else:
            df_agg = df_agg.max(level="site_name")

        # add to summary dataframe
        df_agg.rename(columns={'precip_mm': date}, inplace=True)
        summary_df = summary_df.join(df_agg[date])
    return summary_df


def zero_sum_days_to_nan(raw_df):
    dates = get_date_range()
    for site in raw_df.site_name.unique():
        df1 = raw_df[raw_df.site_name == site]
        df1.set_index('datetime', inplace=True)
        for date in dates:
            try:
                if df1[date].precip_mm.sum() == 0 and not df1[date].empty:
                    print site, ",", date
                    raw_df.loc[df1[date]['index'], 'precip_mm'] = np.nan
            except KeyError:
                continue
    return raw_df


def create_summary_table(summ_df, mdih, mdif, dty, file_name):
    dur_df = get_storm_durations(summ_df, get_date_range(), 0.025)
    overall_summary_df_by_date = dur_df.join(pd.DataFrame(
        {'mean_total_rainfall_volume (mm)': summ_df.mean()})
    )
    overall_summary_df_by_date = overall_summary_df_by_date.join(
        pd.DataFrame({'st. dev (mm)': summ_df.std()})
    )
    overall_summary_df_by_date['average_intensity (mm/hr)'] = \
        overall_summary_df_by_date['mean_total_rainfall_volume (mm)'] /\
        overall_summary_df_by_date['duration (hr)']
    overall_summary_df_by_date = overall_summary_df_by_date.join(
        pd.DataFrame({'mean_max_hourly_intensity (mm/hr)': mdih.mean()})
    )
    overall_summary_df_by_date = overall_summary_df_by_date.join(
        pd.DataFrame({'max_max_hourly_intensity (mm/hr)': mdih.max()})
    )
    overall_summary_df_by_date = overall_summary_df_by_date.join(
        pd.DataFrame({'mean_max_15min_intensity (mm/15 min)': mdif.mean()})
    )
    overall_summary_df_by_date = overall_summary_df_by_date.join(pd.DataFrame(
        {'max_max_15min_intensity (mm/15 min)': mdif.max()})
    )

    # write to csv file ##
    overall_summary_df_by_date.to_csv("{}{}.csv".format(check_dir(dty), file_name))


def reformat_dates(dr):
    formatted = []
    for date in dr:
        date = datetime.datetime.strptime(str(date), '%Y%m%d').strftime('%Y-%m-%d')
        formatted.append(date)
    return formatted


def update_table(table_name, df):
    con = sqlite3.connect(db_filename)
    c = con.cursor()
    c.execute('DROP TABLE {}'.format(table_name))
    df.to_sql(table_name, con)


def update_db(table_name):
    """
    :param table_name: should be 'fif', 'daily' or 'hr'
    :return:
    """
    if table_name == 'daily':
        df = get_daily_tots_df()

    else:
        if table_name == 'fif':
            dfs = get_subdaily_df('15T')
        elif table_name == 'hr':
            dfs = get_subdaily_df('H')
        df = combine_sub_daily_dfs(dfs)
    update_table(table_name, df)
    return df


def check_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)
    return d

