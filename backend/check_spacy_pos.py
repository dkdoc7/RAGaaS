import spacy
nlp = spacy.load("ko_core_news_sm")
doc = nlp("시즌 2의")
for token in doc:
    print(f"{token.text} {token.pos_} {token.tag_}")
