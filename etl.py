import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    ''' 
    From the 'data/song_data' directory, extract information from the JSON files
    and use those values to populate the 'artists' and 'songs' tables.
    '''
    
    # open song file
    df = pd.read_json(filepath, dtype={'year': int}, lines=True)

    for index, row in df.iterrows():
        # insert song record
        song_data = (row.song_id, row.title, row.artist_id, row.year, row.duration)
        
        try:
            cur.execute(song_table_insert, song_data)
        except psycopg2.Error as e:
            print("error Inserting row for table: songs")
            print(e)

        # insert artist record
        artist_data = (row.artist_id, row.artist_name, row.artist_location, row.artist_latitude, row.artist_longitude)
        
        try:
            cur.execute(artist_table_insert, artist_data)
        except psycopg2.Error as e:
            print("Error: Inserting row for table: artists")
            print(e)


def process_log_file(cur, filepath):
    ''' 
    From the 'data/log_data' directory, extract information from the JSON files
    and use those values to populate the 'time', 'users', and 'songplays' tables.
    
    The 'songplays' table is populated with the song_id and artist_id from the 'songs' and 'artists' tables.
    '''
    
    # open log file
    df = pd.read_json(filepath, lines=True)

    # filter by NextSong action
    df = df[df.page == 'NextSong']

    # convert timestamp column to datetime (milliseconds)
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    t = df.copy()
    
    # insert time data records
    # Extract the timestamp, hour, day, week of year, month, year, and weekday 
    # from the ts column and set time_data to a list containing these values in order
    time_data = (t.ts, t.ts.dt.hour, t.ts.dt.day, t.ts.dt.week, t.ts.dt.month, t.ts.dt.year, t.ts.dt.weekday)
    
    # Specify labels for these columns and set to column_labels
    column_labels = ('start_time', 'hour', 'day', 'week', 'month', 'year', 'weekday')
    
    # Create a dataframe, time_df, containing the time data for this file by combining 
    # column_labels and time_data into a dictionary and converting this into a dataframe
    time_df = pd.DataFrame.from_dict(dict(zip(column_labels, time_data)))

    for i, row in time_df.iterrows():
        try:
            cur.execute(time_table_insert, list(row))
        except psycopg2.Error as e:
            print("Error: Inserting row for table: time")
            print(e)

    # load user table
    user_df = df[['userId', 'firstName', 'lastName', 'gender', 'level']]

    # insert user records
    for i, row in user_df.iterrows():
        try:
            cur.execute(user_table_insert, row)
        except psycopg2.Error as e:
            print("Error: Inserting row for table: users")
            print(e)

    # insert songplay records
    for index, row in df.iterrows():
        
        # get songid and artistid from song and artist tables
        try:
            cur.execute(song_select, (row.song, row.artist, row.length))
            results = cur.fetchone()

            if results:
                songid, artistid = results
            else:
                songid, artistid = None, None

            # insert songplay record
            songplay_data = (row.ts, row.userId, row.level, songid, artistid, row.sessionId, row.location, row.userAgent)
            
            try:
                cur.execute(songplay_table_insert, songplay_data)
            except psycopg2.Error as e:
                print("Error: Inserting row for table: songplays")
                print(e)
            
        except psycopg2.Error as e:
            print("Error: Querying for Song ID and Artist ID")
            print(e)


def process_data(cur, conn, filepath, func):
    '''
    Use each individual JSON file to populate the 5 SQL tables.
    '''
    
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process using the specified function passed through 'func'
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    '''
    Creates and connects to the sparkifydb
    Returns the connection and cursor to sparkifydb
    '''
    
    try:
        conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    except psycopg2.Error as e:
        print("Error: Could not make connection to the Postgres database")
        print(e)
        
    try:
        cur = conn.cursor()
    except psycopg2.Error as e:
        print("Error: Could not get cursor to the database")
        print(e)

    '''
    Pulls the list of all JSON files in the 'data' directory
    Sends those filepaths to the 'process_data' function
    '''
    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()