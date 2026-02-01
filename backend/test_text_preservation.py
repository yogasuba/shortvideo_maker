# Test to verify text preservation through the pipeline

test_tamil = "இந்தியாவின் புக்கிய பிதா தலங்களின் பட்டியலில், திலதர்ப்பணபுரி ஓர் முக்கிய இடம் பிடிக்கிறது."

# Simulate what happens in the code
words = test_tamil.split(' ')
print(f"Original: {test_tamil}")
print(f"Words: {words}")
print(f"Rejoined: {' '.join(words)}")
print(f"Match: {test_tamil == ' '.join(words)}")

# Check if split() vs split(' ') makes a difference
words1 = test_tamil.split()
words2 = test_tamil.split(' ')
print(f"\nsplit(): {words1}")
print(f"split(' '): {words2}")
print(f"Same: {words1 == words2}")
