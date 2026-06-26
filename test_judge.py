from judge import Judge

judge = Judge()

result = judge.evaluate(
    question="What is the height of Mount Everest?",
    article="Mount Everest",
    answer="Mount Everest is 8,848.86 metres (29,031.7 ft) high."
)

print(result)