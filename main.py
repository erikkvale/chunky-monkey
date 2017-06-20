import csv
import os
import tempfile
import pandas as pd
from datasources.mssql import MSSqlDb
from pandas.errors import ParserError


def chunky_monkey_csv_loader(csv_file_path,
                             sqlalchemy_engine,
                             sql_schema_name,
                             sql_table_name,
                             bulk_insert=True,
                             included_columns=None,
                             chunk_size=10000):
    """
    Reads the specified csv file by chunks, each chunk is a Pandas dataframe
    and is loaded in to the specified SQL database by each unit chunk. This
    chunking is specified in the documentation for the Pandas.Dataframe.read_csv()
    method and the iterator object returned when 'chunksize' is specified. If
    bulk_insert=True, then utilize the SQL flavor's bulk insert method if available.
    If bulk_insert=False, then use the Pandas.Dataframe.to_sql() method; although,
    depending on the DBAPI used in the SQLAlchemy connection, this could be very
    slow, so bulk_insert=True is the default.
    """

    chunk_iterator = pd.read_csv(filepath_or_buffer=csv_file_path,
                                 usecols=included_columns,
                                 iterator=True,
                                 chunksize=chunk_size)
    for chunk in chunk_iterator:
        if bulk_insert:
            try:
                # delete=False and manual close and delete for Windows NT:
                # https://docs.python.org/3/library/tempfile.html
                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_csv:
                    chunk.to_csv(temp_csv.name, header=False, columns=columns_to_include)
                    temp_csv.close()
                    sql_db.bulk_insert(csv_file_path=temp_csv.name,
                                       sql_schema_name=sql_schema_name,
                                       sql_table_name=sql_table_name,
                                       field_terminator=',',
                                       row_terminator='\\n')

            except Exception as e:
                print(e)
            except ParserError as p:
                print('Check that the file is not malformed')
            finally:
                os.unlink(temp_csv.name)
        else:
            chunk.to_sql(sql_table_name, sql_db.engine, sql_schema_name, if_exists='append')


if __name__=='__main__':

    big_csv_file = r'C:\Users\Erik\Documents\University of Idaho\Projects\data\COND.csv'

    conn_dict = {
        'DRIVER': 'ODBC Driver 13 for SQL Server',
        'SERVER': 'ORION\TARS',
        'DATABASE': 'Data_Raju',
        'Trusted_Connection': 'yes'
    }

    sql_db = MSSqlDb(connection_dict=conn_dict)

    # TREE.csv: columns_to_include = ['PLT_CN', 'INVYR', 'CONDID', 'STATECD', 'COUNTYCD', 'CYCLE', 'PLOT', 'DRYBIO_AG', 'DRYBIO_BG']
    # COND.csv: columns_to_include = ['PLT_CN', 'INVYR', 'CONDID', 'STATECD', 'COUNTYCD', 'CYCLE', 'PLOT']
    # PLOTSNAP.csv: columns_to_include = ['CN', 'INVYR', 'CONDID', 'STATECD', 'COUNTYCD', 'CYCLE', 'PLOT']
    
    chunky_monkey_csv_loader(csv_file_path=big_csv_file,
                             sqlalchemy_engine=sql_db.engine,
                             sql_schema_name='dbo',
                             sql_table_name='Cond',
                             included_columns=columns_to_include,
                             chunk_size=500000)
