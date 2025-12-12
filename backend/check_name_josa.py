import spacy

nlp = spacy.load("ko_core_news_sm")

def simulate_clean(name_with_josa):
    doc = nlp(name_with_josa)
    last_token = doc[-1]
    
    print(f"Input: {name_with_josa}")
    print(f"  Last Token: {last_token.text}, POS: {last_token.pos_}, TAG: {last_token.tag_}, LEMMA: {last_token.lemma_}")
    
    # Current Logic Simulation
    clean_last = last_token.text
    
    # Checks
    if '+' in last_token.lemma_:
        parts = last_token.lemma_.split('+')
        if len(parts) >= 2:
            clean_last = parts[0]
            print(f"  -> Lemma Split: {clean_last}")
            
    # Fallback Suffix
    josas = ['의', '은', '는', '이', '가', '을', '를', '에', '와', '과', '로', '으로', '에서', '에게', '께', '부터', '까지', '도', '만']
    for josa in sorted(josas, key=len, reverse=True):
         if clean_last.endswith(josa) and len(clean_last) > len(josa):
             clean_last = clean_last[:-len(josa)]
             print(f"  -> Suffix Strip: {clean_last}")
             break
             
    print(f"  -> Final: {clean_last}")
    print("-" * 20)

samples = ["이정재가", "이정재는", "이정재의", "공유가", "송중기는"]
for s in samples:
    simulate_clean(s)
