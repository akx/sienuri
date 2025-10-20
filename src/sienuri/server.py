import duckdb
import orjson
from starlette.applications import Starlette
from starlette.responses import Response

app = Starlette()


async def query_endpoint(request):
    params = request.query_params
    sql = params["sql"]
    with duckdb.connect(database="topo.duckdb", read_only=True) as con:
        rows = list(con.execute(sql).fetchall())
        desc = con.description
    columns = [d[0] for d in desc]
    result = {"columns": columns, "rows": rows}
    dat = orjson.dumps(result)
    return Response(dat, media_type="application/json")


app.add_route("/api/query", query_endpoint)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("sienuri.server:app", host="0", port=9420, reload=True)
