from flask import Flask, request, jsonify
import dns.message
import dns.rdatatype
import httpx

app = Flask(__name__) # TROCAR PARA FAST API ASSINCRONO

# Config
DNSDIST_URL = "https://dnsdist/dns-query"

@app.route('/resolve', methods=['GET'])
def resolve_dns():
    # Receiving URL/Domain from GET parameter
    domain = request.args.get('url')
    rd = request.args.get('record')

    if not domain:
        return jsonify({"erro": "Parametro 'url' obrigatório"}), 400

    try:
        # translate
        # Creating DNS question (Type A = IPv4)
        q = dns.message.make_query(domain, dns.rdatatype.from_text(rd))
        # print(q) # debug only
        wire_data = q.to_wire()
        # print(wire_data) # debug only
    
        # Sending binary to dnsdist
        with httpx.Client(verify=False, http2=True) as client:
            response = client.post(
                DNSDIST_URL,
                headers={
                    "Content-Type": "application/dns-message",
                    "Accept": "application/dns-message"
                },
                content=wire_data,
                timeout=5.0
            )
        if response.status_code != 200:
            return jsonify({"erro_dnsdist": response.status_code, "msg": response.text}), 502
        
        # Decoding (Binary -> JSON)
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

        return jsonify({
            "Status": dns.rcode.to_text(dns_response.rcode()),
            "Question": [{"name": domain, "type": rd}],
            "Answer": full_answers
        })
    
    except Exception as e:
        return jsonify({"erro_interno": str(e)}), 500
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)