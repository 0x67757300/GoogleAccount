#!/usr/bin/env python3

import sys
import time
import hashlib
import sqlite3
import httpx
import jinja2
import uhttp
import uvicorn


jenv = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))
app = uhttp.Application()
cookies = httpx.Cookies()


@app.get("/")
async def query(request):
    email = request.args.get("email")
    template = jenv.get_template("index.html")

    if not email:
        return template.render()

    async with httpx.AsyncClient(http2=True, timeout=15) as client:
        origin = "https://photos.google.com"
        timestamp = int(time.time())
        sapisidhash = hashlib.sha1(f"{timestamp} {cookies.get('SAPISID')} {origin}".encode()).hexdigest()
        r = await client.get(
            "https://people-pa.clients6.google.com/v2/people/lookup",
            params={
                "id": email,
                "type": "EMAIL",
                "matchType": "EXACT",
                "requestMask.includeField.paths": ["person.metadata", "person.name", "person.email", "person.photo", "person.cover_photo"],
                "core_id_params.enable_private_names": True
            },
            headers={
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; rv:68.0) Gecko/20100101 Firefox/68.0",
                "x-goog-api-key": "AIzaSyAa2odBewW-sPJu3jMORr0aNedh3YlkiQc",
                "origin": origin,
                "referer": origin,
                "authorization": f"SAPISIDHASH {timestamp}_{sapisidhash}"
            },
            cookies=cookies
        )

    r = list(r.json().get("people", {"_": {}}).values())[0]

    return template.render(context={
        "id": r.get("personId"),
        "name": r.get("name", [{}])[0].get("displayName"),
        "email": r.get("email", [{}])[0].get("value"),
        "picture": r.get("photo", [{}])[0].get("url"),
        "cover": r.get("coverPhoto", [{}])[0].get("imageUrl"),
    })


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <cookies.sqlite>", file=sys.stderr)
        exit(1)

    cookies.update(sqlite3.connect(sys.argv[1]).execute(
        "SELECT name,value FROM moz_cookies WHERE host='.google.com'"
    ).fetchall())

    uvicorn.run("__main__:app")
