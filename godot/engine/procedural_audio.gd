class_name ProceduralAudio
extends RefCounted

const SAMPLE_RATE := 44100
const PEAK_VOL := 0.95
const MAX_16BIT := 32767
const PEAK_16BIT := int(MAX_16BIT * PEAK_VOL)

var _cache: Dictionary = {}
var _rng: RandomNumberGenerator

func _init(seed_val: int = 0) -> void:
	_rng = RandomNumberGenerator.new()
	_rng.seed = seed_val

func clear_cache() -> void:
	_cache.clear()

func _generate_wav(samples: PackedFloat32Array, loop: bool = false, loop_begin: int = 0, loop_end: int = 0) -> AudioStreamWAV:
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = SAMPLE_RATE
	wav.stereo = false
	
	var bytes := PackedByteArray()
	bytes.resize(samples.size() * 2)
	
	for i in range(samples.size()):
		var s := clampf(samples[i], -PEAK_VOL, PEAK_VOL)
		var val := int(s * MAX_16BIT)
		bytes.encode_s16(i * 2, val)
		
	wav.data = bytes
	if loop:
		wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
		wav.loop_begin = loop_begin
		wav.loop_end = loop_end if loop_end > 0 else samples.size()
	return wav

func _noise() -> float:
	return _rng.randf_range(-1.0, 1.0)

# ----------------- SFX GENERATORS -----------------

func get_sfx_hit() -> AudioStreamWAV:
	var key := "hit"
	if _cache.has(key): return _cache[key]
	var len_s := 0.15
	var samples := PackedFloat32Array()
	var total := int(len_s * SAMPLE_RATE)
	samples.resize(total)
	for i in range(total):
		var t := float(i) / SAMPLE_RATE
		var env := exp(-t * 30.0)
		var osc := _noise() * 0.5 + sin(t * TAU * 150.0) * 0.5
		samples[i] = osc * env
	var w: AudioStreamWAV = _generate_wav(samples)
	_cache[key] = w
	return w

func get_sfx_crit() -> AudioStreamWAV:
	var key := "crit"
	if _cache.has(key): return _cache[key]
	var len_s := 0.25
	var samples := PackedFloat32Array()
	var total := int(len_s * SAMPLE_RATE)
	samples.resize(total)
	for i in range(total):
		var t := float(i) / SAMPLE_RATE
		var env := exp(-t * 20.0)
		var osc := sin(t * TAU * (800.0 - t * 2000.0)) * 0.5 + _noise() * 0.5
		samples[i] = osc * env
	var w: AudioStreamWAV = _generate_wav(samples)
	_cache[key] = w
	return w

func get_sfx_pickup() -> AudioStreamWAV:
	var key := "pickup"
	if _cache.has(key): return _cache[key]
	var len_s := 0.2
	var samples := PackedFloat32Array()
	var total := int(len_s * SAMPLE_RATE)
	samples.resize(total)
	for i in range(total):
		var t := float(i) / SAMPLE_RATE
		var env := exp(-t * 15.0)
		var freq = 1200.0 if t < 0.1 else 1600.0
		var osc := sin(t * TAU * freq)
		samples[i] = osc * env
	var w: AudioStreamWAV = _generate_wav(samples)
	_cache[key] = w
	return w

func get_sfx_door() -> AudioStreamWAV:
	var key := "door"
	if _cache.has(key): return _cache[key]
	var len_s := 0.4
	var samples := PackedFloat32Array()
	var total := int(len_s * SAMPLE_RATE)
	samples.resize(total)
	for i in range(total):
		var t := float(i) / SAMPLE_RATE
		var env := exp(-t * 10.0)
		var osc := _noise() * 0.8 + sin(t * TAU * 50.0) * 0.2
		samples[i] = osc * env
	var w: AudioStreamWAV = _generate_wav(samples)
	_cache[key] = w
	return w

func get_sfx_torch() -> AudioStreamWAV:
	var key := "torch"
	if _cache.has(key): return _cache[key]
	var len_s := 0.3
	var samples := PackedFloat32Array()
	var total := int(len_s * SAMPLE_RATE)
	samples.resize(total)
	for i in range(total):
		var t := float(i) / SAMPLE_RATE
		var env := exp(-t * 5.0)
		var osc := _noise() * 0.6 + sin(t * TAU * (300.0 + _noise()*50.0)) * 0.4
		samples[i] = osc * env
	var w: AudioStreamWAV = _generate_wav(samples)
	_cache[key] = w
	return w

func get_sfx_heartbeat() -> AudioStreamWAV:
	var key := "heartbeat"
	if _cache.has(key): return _cache[key]
	var len_s := 0.4
	var samples := PackedFloat32Array()
	var total := int(len_s * SAMPLE_RATE)
	samples.resize(total)
	for i in range(total):
		var t := float(i) / SAMPLE_RATE
		var env1 := exp(-t * 40.0)
		var env2 := exp(-(t - 0.15) * 40.0) if t > 0.15 else 0.0
		var osc := sin(t * TAU * 60.0)
		samples[i] = osc * (env1 + env2 * 0.8)
	var w: AudioStreamWAV = _generate_wav(samples)
	_cache[key] = w
	return w

func get_sfx_secret() -> AudioStreamWAV:
	var key := "secret"
	if _cache.has(key): return _cache[key]
	var len_s := 0.6
	var samples := PackedFloat32Array()
	var total := int(len_s * SAMPLE_RATE)
	samples.resize(total)
	for i in range(total):
		var t := float(i) / SAMPLE_RATE
		var env := exp(-t * 5.0)
		var freq := 800.0 + sin(t * TAU * 10.0) * 200.0
		var osc := sin(t * TAU * freq) * 0.5 + sin(t * TAU * freq * 1.5) * 0.25
		samples[i] = osc * env
	var w: AudioStreamWAV = _generate_wav(samples)
	_cache[key] = w
	return w

func get_sfx_ledge_jump() -> AudioStreamWAV:
	var key := "ledge_jump"
	if _cache.has(key): return _cache[key]
	var len_s := 0.22
	var samples := PackedFloat32Array()
	var total := int(len_s * SAMPLE_RATE)
	samples.resize(total)
	for i in range(total):
		var t := float(i) / SAMPLE_RATE
		var env := exp(-t * 14.0)
		var freq := 340.0 + t * 1800.0
		samples[i] = sin(t * TAU * freq) * env * 0.65
	var w: AudioStreamWAV = _generate_wav(samples)
	_cache[key] = w
	return w

# ----------------- AMBIENCE GENERATORS -----------------

func get_ambient_layer(elevation: int) -> AudioStreamWAV:
	elevation = clampi(elevation, -2, 2)
	var key := "ambient_" + str(elevation)
	if _cache.has(key): return _cache[key]
	
	# Create a seamless 1-second loop
	var len_s := 1.0
	var total := int(len_s * SAMPLE_RATE)
	var samples := PackedFloat32Array()
	samples.resize(total)
	
	var base_freq := 55.0 - (elevation * 10.0) # Lower pitch for deeper
	var mod_freq := 0.5 + (elevation * 0.1)
	
	for i in range(total):
		var t := float(i) / SAMPLE_RATE
		var phase := t * TAU
		var osc1 := sin(phase * base_freq)
		var osc2 := sin(phase * base_freq * 1.5) * 0.5
		
		var mod_int: float = round(mod_freq) if mod_freq >= 1.0 else 1.0
		var am := sin(phase * mod_int) * 0.2 + 0.8
		
		var noise_val := _noise() * 0.1 * (2 - elevation) / 4.0
		
		samples[i] = (osc1 + osc2 + noise_val) * 0.3 * am
		
	var blend_samples := 100
	var first_val := samples[0]
	for i in range(blend_samples):
		var idx := total - blend_samples + i
		var factor := float(i) / blend_samples
		samples[idx] = lerp(samples[idx], first_val, factor)
		
	var w: AudioStreamWAV = _generate_wav(samples, true, 0, total)
	_cache[key] = w
	return w

# ----------------- STINGER GENERATOR -----------------

func get_stinger(intensity: float) -> AudioStreamWAV:
	var key := "stinger_" + str(intensity)
	if _cache.has(key): return _cache[key]
	
	var len_s := 1.5
	var total := int(len_s * SAMPLE_RATE)
	var samples := PackedFloat32Array()
	samples.resize(total)
	
	for i in range(total):
		var t := float(i) / SAMPLE_RATE
		var env := (1.0 - t/len_s)
		env *= env
		
		var freq := 100.0 * (1.0 + intensity)
		var osc := sin(t * TAU * freq) * 0.4
		var fosc := sin(t * TAU * freq * 2.01) * 0.2
		var tosc := sin(t * TAU * freq * 3.02) * 0.1
		var n := _noise() * 0.3 * intensity
		
		samples[i] = (osc + fosc + tosc + n) * env
		
	var w: AudioStreamWAV = _generate_wav(samples)
	_cache[key] = w
	return w
