from fastapi import FastAPI, HTTPException
import dns.message
import dns.rdatatype
import httpx

# Using fast api to make async requests and make app more simple
app = FastAPI(tittle="DoH-loadBalancer")

# Config
DNSDIST_URL = "https://dnsdist/dns-query"
client: httpx.AsyncClient | None = None

@app.on_event("startup")
async def startup_event():
    global client
    client = httpx.AsyncClient(verify=False, http2=True, timeout=5.0)  # change verify=False to True for production
    

@app.on_event("shutdown")
async def shutdown_event():
    global client
    await client.aclose()

@app.get("/resolve")
async def resolve_dns(url: str, type: str = "A"):
    global client

    # Solving a domain using backend DNSDist by DoH
    if not url:
        raise HTTPException(status_code=400, detail="Parametro 'url' obrigatório!")
    
    try:
        rdtype = dns.rdatatype.from_text(type)
    except (dns.rdatatype.UnknownRdatatype, ValueError):
        raise HTTPException(status_code=400, detail=f"Tipo de registro inválido : {type}")

    try:
        # Getting query
        q = dns.message.make_query(url, rdtype)
        wire_data = q.to_wire()

        # Sending to dnsdist async
        response = await client.post(
            DNSDIST_URL,
            headers={"ContentType": "application/dns-message"},
            content=wire_data,
            timeout=5.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Erro no DNSDist: {response.text}")
        
        # Decoding answer
        dns_response = dns.message.from_wire(response.content)

        full_answers = []
        for rrset in dns_response.answer:
            rtype = dns.rdatatype.to_text(rrset.rdtype)
            for rr in rrset:
                full_answers.append({
                    "name": str(rrset.name),
                    "type": rtype,
                    "ttl": rrset.ttl,
                    "data": str(rr)
                })
        
        # Direct return
        return {
            "Status": dns.rcode.to_text(dns_response.rcode()),
            "Question": [{"name": url, "type": type.upper()}],
            "Answer": full_answers
        }
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Erro de conexão com DNSDist: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))