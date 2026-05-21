import psycopg

def revert_mock_data():
    conn = psycopg.connect("postgresql://marimo:marimo@db-server:5432/marimo")
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("DELETE FROM sensor_readings WHERE sensor_type = 'hourly'")
    print("Deleted hourly mock data.")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    revert_mock_data()
