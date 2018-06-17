pairs = ["btcusd","ltcusd","ltcbtc","ethusd","ethbtc","etcbtc","etcusd","rrtusd","rrtbtc","zecusd","zecbtc","xmrusd","xmrbtc","dshusd","dshbtc","btceur","btcjpy","xrpusd","xrpbtc","iotusd","iotbtc","ioteth","eosusd","eosbtc","eoseth","sanusd","sanbtc","saneth","omgusd","omgbtc","omgeth","bchusd","bchbtc","bcheth","neousd","neobtc","neoeth","etpusd","etpbtc","etpeth","qtmusd","qtmbtc","qtmeth","avtusd","avtbtc","avteth","edousd","edobtc","edoeth","btgusd","btgbtc","datusd","datbtc","dateth","qshusd","qshbtc","qsheth","yywusd","yywbtc","yyweth","gntusd","gntbtc","gnteth","sntusd","sntbtc","snteth","ioteur","batusd","batbtc","bateth","mnausd","mnabtc","mnaeth","funusd","funbtc","funeth","zrxusd","zrxbtc","zrxeth","tnbusd","tnbbtc","tnbeth","spkusd","spkbtc","spketh","trxusd","trxbtc","trxeth","rcnusd","rcnbtc","rcneth","rlcusd","rlcbtc","rlceth","aidusd","aidbtc","aideth","sngusd","sngbtc","sngeth","repusd","repbtc","repeth","elfusd","elfbtc","elfeth","btcgbp","etheur","ethjpy","ethgbp","neoeur","neojpy","neogbp","eoseur","eosjpy","eosgbp","iotjpy","iotgbp","iosusd","iosbtc","ioseth","aiousd","aiobtc","aioeth","requsd","reqbtc","reqeth","rdnusd","rdnbtc","rdneth","lrcusd","lrcbtc","lrceth","waxusd","waxbtc","waxeth","daiusd","daibtc","daieth","cfiusd","cfibtc","cfieth","agiusd","agibtc","agieth","bftusd","bftbtc","bfteth","mtnusd","mtnbtc","mtneth","odeusd","odebtc","odeeth","antusd","antbtc","anteth","dthusd","dthbtc","dtheth","mitusd","mitbtc","miteth","stjusd","stjbtc","stjeth","xlmusd","xlmeur","xlmjpy","xlmgbp","xlmbtc","xlmeth","xvgusd","xvgeur","xvgjpy","xvggbp","xvgbtc","xvgeth","bciusd","bcibtc","mkrusd","mkrbtc","mkreth","venusd","venbtc","veneth","kncusd","kncbtc","knceth","poausd","poabtc","poaeth","lymusd","lymbtc","lymeth","utkusd","utkbtc","utketh","veeusd","veebtc","veeeth","dadusd","dadbtc","dadeth","orsusd","orsbtc","orseth","aucusd","aucbtc","auceth","poyusd","poybtc","poyeth","fsnusd","fsnbtc","fsneth","cbtusd","cbtbtc","cbteth"]
tracking = ["BTC", "EOS", "ETH", "BCH", "ETC", "XRP", "LTC", "MIOTA", "NEO", "XMR", "DASH", "BTG", "ZEC", "BCI", "XVG", "QTUM", "XLM", "ETP"]
count = 0
nope = []
yep = []
for pair in pairs:
	p = pair.upper();
	m = count
	for coin in tracking:
		if coin in p[:4]:
			count += 1
			#print("pub static %s : &'static str = \"%s\";" % (p, p));
			#print("('%d', '%s')," % (count, p))
	if count == m:
		nope.append(p);
	else:
		yep.append(p);

print(count)
print(''.join('"{}", '.format(k) for k in yep))

notused = [
'RRTUSD', 'RRTBTC', 'DSHUSD', 'DSHBTC', 'IOTUSD', 'IOTBTC', 'IOTETH', 'SANUSD', 'SANBTC', 'SANETH', 
'OMGUSD', 'OMGBTC', 'OMGETH', 'QTMUSD', 'QTMBTC', 'QTMETH', 'AVTUSD', 'AVTBTC', 'AVTETH', 'EDOUSD', 
'EDOBTC', 'EDOETH', 'DATUSD', 'DATBTC', 'DATETH', 'QSHUSD', 'QSHBTC', 'QSHETH', 'YYWUSD', 'YYWBTC', 
'YYWETH', 'GNTUSD', 'GNTBTC', 'GNTETH', 'SNTUSD', 'SNTBTC', 'SNTETH', 'IOTEUR', 'BATUSD', 'BATBTC', 
'BATETH', 'MNAUSD', 'MNABTC', 'MNAETH', 'FUNUSD', 'FUNBTC', 'FUNETH', 'ZRXUSD', 'ZRXBTC', 'ZRXETH', 
'TNBUSD', 'TNBBTC', 'TNBETH', 'SPKUSD', 'SPKBTC', 'SPKETH', 'TRXUSD', 'TRXBTC', 'TRXETH', 'RCNUSD', 
'RCNBTC', 'RCNETH', 'RLCUSD', 'RLCBTC', 'RLCETH', 'AIDUSD', 'AIDBTC', 'AIDETH', 'SNGUSD', 'SNGBTC', 
'SNGETH', 'REPUSD', 'REPBTC', 'REPETH', 'ELFUSD', 'ELFBTC', 'ELFETH', 'IOTJPY', 'IOTGBP', 'IOSUSD', 
'IOSBTC', 'IOSETH', 'AIOUSD', 'AIOBTC', 'AIOETH', 'REQUSD', 'REQBTC', 'REQETH', 'RDNUSD', 'RDNBTC', 
'RDNETH', 'LRCUSD', 'LRCBTC', 'LRCETH', 'WAXUSD', 'WAXBTC', 'WAXETH', 'DAIUSD', 'DAIBTC', 'DAIETH', 
'CFIUSD', 'CFIBTC', 'CFIETH', 'AGIUSD', 'AGIBTC', 'AGIETH', 'BFTUSD', 'BFTBTC', 'BFTETH', 'MTNUSD', 
'MTNBTC', 'MTNETH', 'ODEUSD', 'ODEBTC', 'ODEETH', 'ANTUSD', 'ANTBTC', 'ANTETH', 'DTHUSD', 'DTHBTC', 
'DTHETH', 'MITUSD', 'MITBTC', 'MITETH', 'STJUSD', 'STJBTC', 'STJETH', 'MKRUSD', 'MKRBTC', 'MKRETH', 
'VENUSD', 'VENBTC', 'VENETH', 'KNCUSD', 'KNCBTC', 'KNCETH', 'POAUSD', 'POABTC', 'POAETH', 'LYMUSD', 
'LYMBTC', 'LYMETH', 'UTKUSD', 'UTKBTC', 'UTKETH', 'VEEUSD', 'VEEBTC', 'VEEETH', 'DADUSD', 'DADBTC', 
'DADETH', 'ORSUSD', 'ORSBTC', 'ORSETH', 'AUCUSD', 'AUCBTC', 'AUCETH', 'POYUSD', 'POYBTC', 'POYETH', 
'FSNUSD', 'FSNBTC', 'FSNETH', 'CBTUSD', 'CBTBTC', 'CBTETH']



used = [
'BTCUSD', 'LTCUSD', 'LTCBTC', 'ETHUSD', 'ETHBTC', 'ETCBTC', 'ETCUSD', 'ZECUSD', 'ZECBTC', 'XMRUSD', 
'XMRBTC', 'BTCEUR', 'BTCJPY', 'XRPUSD', 'XRPBTC', 'EOSUSD', 'EOSBTC', 'EOSETH', 'BCHUSD', 'BCHBTC', 
'BCHETH', 'NEOUSD', 'NEOBTC', 'NEOETH', 'ETPUSD', 'ETPBTC', 'ETPETH', 'BTGUSD', 'BTGBTC', 'BTCGBP', 
'ETHEUR', 'ETHJPY', 'ETHGBP', 'NEOEUR', 'NEOJPY', 'NEOGBP', 'EOSEUR', 'EOSJPY', 'EOSGBP', 'XLMUSD', 
'XLMEUR', 'XLMJPY', 'XLMGBP', 'XLMBTC', 'XLMETH', 'XVGUSD', 'XVGEUR', 'XVGJPY', 'XVGGBP', 'XVGBTC', 
'XVGETH', 'BCIUSD', 'BCIBTC']
