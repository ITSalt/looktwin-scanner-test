import random
R=random.Random(2310);A="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";B=A+"_-"
r=lambda n,a:"".join(R.choice(a) for _ in range(n));M="T3Blbk"+"FJ"
C={"proj":lambda:"sk-"+"proj-"+r(74,B)+M+r(74,B),"legacy":lambda:"sk-"+r(20,A)+M+r(20,A),"ours_nomarker":lambda:"sk-"+"proj-"+r(40,B)}
X={"bare":"key {}","query":"https://example.com/v1?key={}&a=1","mdlink":"[k](https://example.com/?key={})","json":'{{"k": "{}"}}',"table":"| run | {} |","comma":"k={},next"}
for c,g in C.items():
    K=[g() for _ in range(1000)]
    for x,t in X.items(): open(f"data/{c}__{x}.txt","w").write("\n".join(t.format(k) for k in K)+"\n")
