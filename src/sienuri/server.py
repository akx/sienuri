import duckdb
from starlette.applications import Starlette

app = Starlette()


async def query_endpoint(request):
    params = request.query_params
    sql = params["sql"]
    with duckdb.connect(database="topo.duckdb", read_only=True) as con:
        result = list(con.execute(sql).fetchall())
    return {"result": result}


app.add_route("/api/query", query_endpoint)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0", port=9420)
