
try:
    from kiwipiepy import Kiwi
    kiwi = Kiwi()
    text = "사과는 맛있다."
    tokens = kiwi.tokenize(text)
    print(f"Text: {text}")
    for t in tokens:
        print(f"Form: {t.form}, Tag: {t.tag}, Start: {t.start}, Len: {t.len}")
except ImportError:
    print("Kiwipiepy not installed.")
