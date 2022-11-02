from sqlalchemy import create_engine
from sqlalchemy.sql import text
import os
# Create your models here.

class Models:
    def __init__(self):
        self.engine = create_engine(os.environ.get('DB_URL', 'postgres://jodxkettrtpizi:8618499d8f2e1c066f0d8833e8eafcbd4f2709dd394ee84c17a3c8625371aaf0@ec2-35-170-21-76.compute-1.amazonaws.com:5432/ddse90s12hm0ae'))

    def executeRawSql(self, statement, params={}):
        out = None
        with self.engine.connect() as con:
            out = con.execute(text(statement), params)
        return out

    def createModels(self):
        self.executeRawSql(
            """CREATE TABLE IF NOT EXISTS crane (
                crane_key INT PRIMARY KEY,
                model TEXT NOT NULL,
                speed INT NOT NULL,
                year_built INT NOT NULL,
                brand TEXT NOT NULL,
                elect_drive TEXT NOT NULL
            );
            """)
        
        self.executeRawSql(
            """CREATE TABLE IF NOT EXISTS fact_table (
                performance INT NOT NULL ,
                mi_rate INT NOT NULL,
                container INT NOT NULL,
                cyc_time TIME NULL,
                crane_key INT NOT NULL,
                date_key DATE NOT NULL,
                maintenance_due_date_key DATE NOT NULL,
                verifier_key INT NOT NULL            
            );
            """)
            
        self.executeRawSql(
            """CREATE TABLE IF NOT EXISTS verifier (
                verifier_key INT PRIMARY KEY,
                verifier_name TEXT NOT NULL,
                verifier_location TEXT NOT NULL,
                verifier_section TEXT NULL,
                verifier_substation TEXT NOT NULL          
            );
            """)
            
        self.executeRawSql(
            """CREATE TABLE IF NOT EXISTS d_date  (
                date_dim_id              INT NOT NULL PRIMARY KEY,
                date_actual              DATE NOT NULL,
                month_actual             INT NOT NULL,
                month_name               VARCHAR(9) NOT NULL,
                month_name_abbreviated   CHAR(3) NOT NULL,
                quarter_actual           CHAR(2) NOT NULL,
                quarter_name             VARCHAR(9) NOT NULL,
                year_actual              INT NOT NULL,
                mmyyyy                   CHAR(6) NOT NULL,
                mmddyyyy                 CHAR(10) NOT NULL       
            );
            """)
            
#         self.executeRawSql(
#             """INSERT INTO d_date
#                 SELECT TO_CHAR(datum, 'yyyymmdd')::INT AS date_dim_id, --
#                 datum AS date_actual,
#                 EXTRACT(MONTH FROM datum)::INT AS month_actual,
#                 TO_CHAR(datum, 'TMMonth') AS month_name,
#                 TO_CHAR(datum, 'Mon') AS month_name_abbreviated,
#                 EXTRACT(QUARTER FROM datum) AS quarter_actual,
#                 CASE
#                     WHEN EXTRACT(QUARTER FROM datum) = 1 THEN 'Q1'
#                     WHEN EXTRACT(QUARTER FROM datum) = 2 THEN 'Q2'
#                     WHEN EXTRACT(QUARTER FROM datum) = 3 THEN 'Q3'
#                     WHEN EXTRACT(QUARTER FROM datum) = 4 THEN 'Q4'
#                     END AS quarter_name,
#                 EXTRACT(YEAR FROM datum)::INT AS year_actual,
#                 TO_CHAR(datum, 'mmyyyy')::CHAR(6) AS mmyyyy,
#                 TO_CHAR(datum, 'mmddyyyy')::CHAR(10) AS mmddyyyy
#                 FROM (SELECT '2022-01-01'::DATE + SEQUENCE.DAY AS datum
#                 FROM GENERATE_SERIES(0, 365) AS SEQUENCE (DAY)
#                 GROUP BY SEQUENCE.DAY) DQ
#                 ORDER BY 1;"""
# )
 
            
    
#class Crane(models.Model):
#    TT_NO = models.CharField(max_length=5,primary_key = True)
#    JOB = models.CharField(max_length=1)
#    Date = models.DateField()
#    IS_MI = models.IntegerField()
#    cyc_time = models.TimeField()