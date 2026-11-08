"""Offline Hindi / Hinglish -> English concept glossary.

This is NOT a translator. It maps a few hundred Hindi story words (Roman-script "Hinglish" spellings and
Devanagari) to the English words the matcher's lexicon understands, drops function words, and moves the verb
forward (Hindi is verb-last, the English event rules expect a verb before its object). Words that are not in
the glossary pass through unchanged (English loanwords, names) or are transliterated (unknown Devanagari).

Written by hand by an AI assistant for this assignment; coverage is limited to common melodrama vocabulary.
Format per line:   [kind:] english | roman variants ; ... | devanagari variants ; ...
  kind  v = verb (moved to the front of its clause)   f = function word (dropped)   (none) = noun / other
  Multi-word variants are allowed and matched longest-first.
"""
from __future__ import annotations

import re

_RAW = r"""
# ---------------- function words (dropped) ----------------
f: | hai; hain; tha; thi; the; ho; hota; hoti; hote; hua; hui; hue; hoga; hogi; honge; raha; rahi; rahe; gaya; gayi; gaye; ka; ki; ke; ko; se; ne; par; pe; mein; me; ek; ye; yeh; wo; woh; us; uska; uski; uske; usne; unka; unki; unke; apna; apni; apne; jo; jis; jise; hi; toh; to; kar; karke; kiya; kiye; kare; kuch; sab; sabhi; bhi; ya; liye; wala; wale; wali; ab; phir; fir; yahan; wahan; tab; jab; kyunki; ki; lekin; magar; aur; tak; sirf; bas; dono; karta; karti; karte; karna; leta; leti; lete; lena; use; usse; unhe; isse; usko; unko; inhe; jaata; jaati; jaate; jaana; kisi; koi | है; हैं; था; थी; थे; हो; होता; होती; होते; हुआ; हुई; हुए; होगा; रहा; रही; रहे; गया; गई; गयी; गए; का; की; के; को; से; ने; पर; पे; में; एक; यह; ये; वह; वो; उस; उसका; उसकी; उसके; उसने; उनका; उनकी; उनके; अपना; अपनी; अपने; जो; जिस; जिसे; ही; तो; कर; करके; किया; किये; किए; करे; कुछ; सब; सभी; भी; या; लिए; वाला; वाले; वाली; अब; फिर; यहाँ; वहाँ; तब; जब; क्योंकि; लेकिन; मगर; और; तक; सिर्फ़; सिर्फ; बस; दोनों; दोनो; उसे; उन्हें; उसको; इसे; कि; करता; करती; करते; करना; लेता; लेती; लेते; लेना; जाता; जाती; जाते; जाना; किसी; कोई
# ---------------- connectors ----------------
and | aur; evam | और; एवं
but | lekin; magar; par; parantu | लेकिन; मगर; परंतु
then | phir; fir; tab | फिर; तब
when | jab | जब
because | kyunki; kyonki | क्योंकि
without | bina; binaa | बिना
not | nahi; nahin; na; nhi | नहीं; ना
# ---------------- numbers / time ----------------
three | teen | तीन
two | do | दो
five | paanch; panch | पाँच; पांच
ten | das | दस
years earlier | saal pehle; sal pehle; varsh pehle | साल पहले; वर्ष पहले
years in the past | saal peeche; saal pichhe | साल पीछे
years later | saal baad; sal baad; saalon baad | साल बाद; सालों बाद
years | saal; saalon; sal | साल; सालों
days | din; dinon | दिन; दिनों
day | din | दिन
night | raat; raatri | रात
morning | subah | सुबह
week | hafta; saptah | हफ़्ता; सप्ताह
month | mahina; mahine | महीना; महीने
# ---------------- people ----------------
wife | patni; biwi; bivi; patnii | पत्नी; बीवी
husband | pati; shauhar; shohar | पति; शौहर
mother | maa; mummy; mata; ammi; maan | माँ; मां; मम्मी; माता; अम्मी
father | papa; pita; baap; pitaji; abbu | पिता; पापा; बाप; पिताजी
daughter | beti | बेटी
son | beta | बेटा
girl | ladki; bachchi; larki | लड़की; बच्ची
boy | ladka; larka | लड़का
children | bachche; bachhe; bacche | बच्चे
child | bachcha; baccha | बच्चा
baby | shishu; nanhi | शिशु
babies | bachche badal |
twin | judwa; jodwa | जुड़वाँ; जुड़वां
brother | bhai | भाई
sister | behen; bahan; behan; behn | बहन
younger sister | chhoti behen; chhoti bahan; choti behen | छोटी बहन
grandfather | nana; dada | नाना; दादा
grandmother | nani; dadi | नानी; दादी
mother-in-law | saas; sas | सास
father-in-law | sasur | ससुर
aunt | chachi; chachiyaan; mausi; bua; mami; maami | चाची; चाचियाँ; चाचियां; मौसी; बुआ; मामी
uncle | chacha; mama; tau; taau | चाचा; मामा; ताऊ
relatives | rishtedaar; rishtedar; rishtedaron | रिश्तेदार; रिश्तेदारों
in-laws | sasural; sasuraal | ससुराल
family | parivaar; pariwar; parivar; gharwale; ghar wale | परिवार; घरवाले; घर वाले
friend | dost; saheli; sahelli; dosti | दोस्त; सहेली
fiancee | mangetar; manghetar | मंगेतर
groom | dulha; dulah | दूल्हा; दूल्हे
bride | dulhan | दुल्हन
guests | mehmaan; mehman; mehmaanon; mehmano | मेहमान; मेहमानों
mistress | premika; girlfriend | प्रेमिका
lover | premi | प्रेमी
servant | naukar; nokar | नौकर
maid | naukrani; nokrani; kaamwali | नौकरानी; कामवाली
driver | driver; chalak | ड्राइवर; चालक
heir | waaris; varis; uttaradhikari | वारिस; उत्तराधिकारी
heiress | heiress |
tycoon | karobari; karobaari; vyapari; businessman; udyogpati | कारोबारी; कारोबार; व्यापारी; बिज़नेसमैन; उद्योगपति
owner | malik; maalik; malkin | मालिक; मालकिन
landlord | makan malik; makaan malik; makanmalik | मकान मालिक
investor | niveshak | निवेशक
stranger | ajnabi | अजनबी
mystery | anjaan; anjan; rahasyamayi | अनजान; रहस्यमयी
rival | pratidwandi; prativandi; pratidwandvi; hariif | प्रतिद्वंदी; प्रतिद्वंद्वी; प्रतिस्पर्धी
enemy | dushman | दुश्मन
doctor | doctor; daktar | डॉक्टर; डाक्टर; डॉ
patient | mareez; mariz; marij | मरीज़; मरीज
nurse | nurse | नर्स
teacher | shikshak; tutor; teacher; adhyapak | शिक्षक; टीचर; ट्यूटर
student | chhatra; student; vidyarthi | छात्र; विद्यार्थी
police | police; pulis | पुलिस
detective | jasoos; detective | जासूस; डिटेक्टिव
criminal | gunehgaar; gunahgar; apradhi | गुनहगार; गुनाहगार; अपराधी
manager | manager | मैनेजर; प्रबंधक
assistant | sachiv; secretary; assistant | सेक्रेटरी; सचिव; असिस्टेंट
intern | intern | इंटर्न
lawyer | vakil | वकील
singer | gayak; gayika | गायक; गायिका
cook | rasoiya | रसोइया
chef | chef | शेफ
# ---------------- places / things ----------------
house | ghar; makan; makaan | घर; मकान
mansion | haveli; bangla; bungalow | हवेली; बंगला
building | building; imarat | बिल्डिंग; इमारत; इमारत
company | company; kampani; firm | कंपनी; कम्पनी
bank | bank | बैंक
brand | brand | ब्रांड; ब्रैंड
restaurant | restaurant; dhaba | रेस्तरां; ढाबा; रेस्टोरेंट
cafe | cafe | कैफ़े; कैफे
school | school; vidyalay | स्कूल; विद्यालय
hospital | aspatal; hospital | अस्पताल; हॉस्पिटल
clinic | clinic | क्लिनिक
village | gaon; gaanv | गाँव; गांव
city | shehar; sheher; nagar | शहर
slum | jhuggi; jhopadi; basti | झुग्गी; झोपड़ी; बस्ती
stall | thela; thele | ठेला; ठेले
studio | studio | स्टूडियो
stage | manch; stage | मंच; स्टेज
screen | screen; parda | स्क्रीन; पर्दा
mandap | mandap | मंडप
altar | mandap | मंडप
party | party | पार्टी
gala | gala | गाला
engagement | mangni; sagai; engagement | मंगनी; सगाई
wedding | shaadi; shadi; vivah; byah | शादी; विवाह
marriage | shaadi; shadi | शादी
anniversary | salgirah; salgira | सालगिरह
launch | launch | लॉन्च
reunion | milan | मिलन
dinner | khana; dinner | खाना; डिनर
rent | kiraya; kiraaya; kirayedaar | किराया
debt | karz; karj; qarz; udhaar; udhar | कर्ज़; कर्ज; क़र्ज़; उधार
money | paisa; paise; rupaye; rakam | पैसा; पैसे; रुपये; रकम
savings | bachat | बचत
wealth | daulat; dolat; sampatti; dhan | दौलत; संपत्ति; धन
inheritance | jaaydaad; jayadad; jaidad; virasat | जायदाद; जायदाद; विरासत
will | vasiyat; vasiyatnama | वसीयत; वसीयतनामा
trust fund | trust fund | ट्रस्ट फंड
contract | contract; anubandh; samjhauta | कॉन्ट्रैक्ट; अनुबंध; समझौता
paper | kaagaz; kagaz; kaghaz; dastavez | कागज़; कागज; दस्तावेज़
evidence | saboot; sabut; saboot | सबूत
proof | prmaan; pramaan | प्रमाण
diary | diary | डायरी
sketchbook | sketchbook | स्केचबुक
sketches | sketches; chitra | स्केच
collection | collection | कलेक्शन
laptop | laptop | लैपटॉप
phone | phone; mobile | फ़ोन; फोन; मोबाइल
recording | recording; record | रिकॉर्डिंग; रिकॉर्ड
conference | conference | कॉन्फ़्रेंस; कॉन्फ्रेंस; कांफ्रेंस
council | council | काउंसिल
licence | license; licence | लाइसेंस
medicine | dawa; dawai; davai | दवा; दवाई
label | label | लेबल
file | file | फ़ाइल; फाइल
report | report | रिपोर्ट
test | test; pariksha; jaanch | टेस्ट; परीक्षा; जाँच
DNA | dna | डीएनए; डी एन ए
eviction notice | eviction notice |
name | naam; nam | नाम
identity | pehchaan; pehchan; asliyat | पहचान; असलियत
truth | sach | सच
lie | jhooth; jhoot; jhuth | झूठ
secret | raaz; raz; rahasya | राज़; राज; रहस्य
life | zindagi; jindagi; jeevan | ज़िंदगी; जिंदगी; जीवन
love | pyaar; pyar; prem; mohabbat | प्यार; प्रेम; मोहब्बत
feelings | jazbaat; bhavna | जज़्बात; भावना
fire | aag; aagzani | आग
accident | durghatna; hadsa; haadsa; accident | दुर्घटना; हादसा; एक्सीडेंट
car | car; gaadi; gadi | कार; गाड़ी
death | maut; mrityu | मौत; मृत्यु
memory | yaaddasht; yaadasht; yaddasht; smriti; memory | याददाश्त; यादाश्त; स्मृति
amnesia lost memory | yaaddasht chali; yaadasht chali; yaaddasht chali jaati | याददाश्त चली
memory returns | yaaddasht laut; yaadasht laut; yaaddasht wapas | याददाश्त लौट; याददाश्त वापस
floor | farsh; farsh | फ़र्श; फर्श
loose floorboard | farsh ke neeche | फ़र्श के नीचे; फर्श के नीचे
policy | niti; policy | नीति; पॉलिसी
# ---------------- descriptors ----------------
rich | ameer; amir; dhani; dhanwaan | अमीर; धनी; धनवान
poor | gareeb; garib; nirdhan | गरीब; ग़रीब; निर्धन
penniless | kangaal; khaali haath | कंगाल; खाली हाथ; ख़ाली हाथ
real | asli; asal; sacchi; sachchi | असली; सच्ची; सच्चा
fake | nakli; jhoota; jhootha; farzi | नकली; झूठा; झूठी; फ़र्ज़ी; फर्जी
useless | nikamma; nikammi | निकम्मा; निकम्मी
powerful | taqatwar; takatwar; shaktishali | ताकतवर; ताक़तवर; शक्तिशाली
old | purana; purani; puraane | पुराना; पुरानी; पुराने
new | naya; nayi; naye | नया; नई; नये; नए
big | bada; badi; bade | बड़ा; बड़ी; बड़े
small | chhota; chhoti; chhote; chota | छोटा; छोटी; छोटे
dying | marta hua; marti hui; bimaar; bimar | मरता हुआ; मरती हुई; बीमार
shy | sharmili; sharmila | शर्मीली; शर्मीला
shocked | hairaan; stabdh | हैरान; स्तब्ध
secretly | chupke se; chupchaap; chupchap; chupke; gupchup | चुपके से; चुपचाप; चुपके; गुपचुप
quietly | chupchaap; chupchap | चुपचाप
slowly | dheere dheere; dhire dhire; dheere | धीरे-धीरे; धीरे धीरे; धीरे
publicly | sabke saamne; sabke samne; sab ke saamne | सबके सामने; सब के सामने
in front of everyone | sabke saamne; sabke samne | सबके सामने
in front of guests | mehmaanon ke saamne; mehmano ke saamne | मेहमानों के सामने
real identity | asli pehchaan; asli pehchan | असली पहचान
under a new name | naye naam se; naya naam; naam badalkar; naam badal kar; naam badal | नए नाम से; नये नाम से; नाम बदलकर; नाम बदल कर
under a false name | jhoote naam; nakli naam | झूठे नाम; नकली नाम
maiden name | maiden naam; maiden name | मेडन नेम
# ---------------- verbs (moved forward) ----------------
v: humiliates | beizzat; beizzati; apmaan; zaleel; zalil; neecha dikhata; neecha dikhate; neecha dikhati | बेइज़्ज़त; बेइज्जत; बेइज़्ज़ती; बेइज्जती; अपमान; नीचा दिखाते; नीचा दिखाता; नीचा दिखाती
v: mocks | mazaak; mazak; majak; mazaaq | मज़ाक; मजाक
v: insults | taane; taana; tane | ताने; ताना
v: betrays | dhokha; dhoka; dhokha | धोखा; धोका
v: cheats | dagabaazi; dagabazi | दग़ाबाज़ी; दगाबाजी
v: has an affair | affair | अफेयर
v: elopes | bhaag jaata; bhaag jaati; bhaag jaate; bhag jata; bhag jati; bhagkar; bhaagkar | भाग जाता; भाग जाती; भाग जाते; भागकर
v: runs away with | ke saath bhaag; ke sath bhag | के साथ भाग; के साथ भाग जाता
v: divorces | talaak; talak; tlak | तलाक
v: thrown out | nikaal diya; nikaal deta; nikal diya; nikaal dete; nikaal di | निकाल दिया; निकाल देता; निकाल दिया जाता; निकाल दिया जाता है; निकाल दी
v: is thrown out | nikaal diya jaata; nikaal diya jaati; bahar nikaal diya | बाहर निकाल दिया
v: leaves | chhod; chhod deta; chhod deti; chhod diya; chhodti; chhodta; chhod diya jaata | छोड़; छोड़ देता; छोड़ देती; छोड़ दिया; छोड़ती; छोड़ता; छोड़ दिया जाता
v: stands by | saath nahi chhodti; saath nahi chhodta | साथ नहीं छोड़ती; साथ नहीं छोड़ता
v: left at the altar | mandap par chhod; mandap pe chhod | मंडप पर छोड़
v: proposes | prastav; prastaav; proposal | प्रस्ताव
v: marries | shaadi karti; shaadi karta; shaadi karte; shaadi karna; shaadi kar | शादी करती; शादी करता; शादी करने; शादी कर
v: falls in love | pyaar karne lagti; pyaar karne lagta; pyaar ho jaata | प्यार करने लगती; प्यार करने लगता; प्यार हो जाता
v: steals | churaata; churaaye; churaya; churati; chori; churane | चुराए; चुराया; चुराता; चुराती; चोरी; चुराने
v: takes credit | credit khud le; credit le leta | क्रेडिट खुद ले; क्रेडिट ले लेता
v: frames | fasaata; fasaaya; fasa diya; fasaya | फँसाता; फंसाता; फँसा दिया; फंसा दिया
v: blames | ilzaam; ilzam; dosh | इल्ज़ाम; इल्जाम; दोष
v: swaps | badal diya; badalwaye; badalwa; badli; badal gaya | बदल दिया; बदलवाए; बदलवाया; बदल दिया गया था; बदल दिया गया
v: swaps at birth | badal diya gaya tha; badal diya gaya | बदल दिया गया था
v: pretends | natak; dikhawa; dikhaava | नाटक; दिखावा
v: disguises himself as | bhes badal; bhes badalkar; roop badal | भेष बदल; भेष बदलकर; रूप बदल
v: reveals | batata; batati; bata deta; bata deti; bataata; bataati; khulasa; khol deti; khol deta; dikhata; dikhati; dikhaata | बताता; बताती; बता देता; बता देती; खुलासा; खोल देती; खोल देता; दिखाता; दिखाती
v: plays the recording | suna deti; suna deta; chala deti; chala deta; sunati; sunata | सुना देती; सुना देता; चला देती; चला देता; सुनाती; सुनाता
v: confesses | kabool kar; kabool kar leti; kabool kar leta; kabul | कबूल कर; कबूल कर लेती; कबूल कर लेता; कबूल
v: admits | maanna padta; maanna padti; maan leti; maan leta; maan lete | मानना पड़ता; मानना पड़ती; मान लेती; मान लेता
v: begs | maangta; maangti; gidgidata; gidgidati; bheek; bheekh | माँगता; मांगता; माँगती; गिड़गिड़ाता; गिड़गिड़ाती; भीख
v: apologises | maafi; mafi; maaf; kshama | माफ़ी; माफी; माफ़; माफ
v: forgives | maaf kar deti; maaf kar deta | माफ़ कर देती; माफ़ कर देता
v: kidnaps | apharan; agwa; agava | अपहरण; अगवा
v: poisons | zeher; jahar | ज़हर; जहर
v: arrested | giraftaar; giraftar; giraftari | गिरफ़्तार; गिरफ्तार; गिरफ़्तारी
v: sends | bhej deti; bhej deta; bhejta; bhejti; bhej | भेज देती; भेज देता; भेजता; भेजती; भेज
v: gives | deta; deti; dete; de deta; de deti; dena | देता; देती; देते; दे देता; दे देती; देना
v: takes a job | naukri; naukri karti; naukri karta | नौकरी; नौकरी करने लगती; नौकरी करने लगता
v: joins | join karti; join karta; shamil | जॉइन करती; जॉइन करता; शामिल
v: becomes | ban jaata; ban jaati; ban jaate; banta; banti | बन जाता; बन जाती; बन जाते; बनता; बनती
v: builds | banati; banata; khada karti; khada karta; kholti; kholta; shuru karti; shuru karta | बनाती; बनाता; खड़ा करती; खड़ा करता; खोलती; खोलता; शुरू करती; शुरू करता
v: wins | jeetti; jeet jaati; jeet jaata; jeetta; jeet | जीतती; जीत जाती; जीत जाता; जीतता; जीत
v: wins clients | jeetne lagti; jeetne lagta | जीतने लगती; जीतने लगता
v: snatches clients | chheenne lagti; chheenne lagta | छीनने लगती; छीनने लगता; छीनने लगती है
v: pays | bhar deta; bhar deti; chukati; chukata; chukane | भर देता; भर देती; चुकाती; चुकाता; चुकाने
v: threatens | dhamki; dhamkee | धमकी
v: evicts | ghar khali karwane; khali karwane | घर खाली करवाने; खाली करवाने
v: tears up | phaad kar; phaad deta; phaad deti; phaad | फाड़ कर; फाड़ देता; फाड़ देती; फाड़
v: announces | elaan; ailaan; ghoshna | ऐलान; घोषणा
v: wakes up | jaag jaati; jaag jaata; aankh kholti; aankh kholta; jaagti | जाग जाती; जाग जाता; आँख खोलती; आँख खोलता
v: remembers | yaad hone; yaad rakhti; yaad rakhta | याद होने; याद रखती; याद रखता
v: changes | badal deti; badal deta; badalti; badalta | बदल देती; बदल देता; बदलती; बदलता
v: records | record kar leti; record kar leta | रिकॉर्ड कर लेती; रिकॉर्ड कर लेता
v: moves out | bahar nikaal leti; door bhej deti; door bhej deta | बाहर निकाल लेती; दूर भेज देती; दूर भेज देता
v: traces | pahunch jaati; pahunch jaata; pahunchti | पहुँच जाती; पहुँच जाता; पहुँचती; पहुंच जाती
v: dies | mar jaata; mar jaati; maut ho jaati; maut ho jaata | मर जाता; मर जाती; मौत हो जाती; मौत हो जाता
v: kills | maar dete; maar deta; maar deti; maar dala; maar diya; maar dena | मार देते; मार देता; मार देती; मार डाला; मार दिया; मार देना
v: sets fire | aag lagakar; aag laga; aag lagana; aag lagata | आग लगाकर; आग लगा; आग लगाना
v: loses licence | licence radd; license radd; lisence radd | लाइसेंस रद्द; लाइसेंस रद्द हो जाता
v: cancelled | radd; radd ho jaata | रद्द
v: tests | imtihaan; imtihan; parakhne; parakh | इम्तिहान; परखने; परखना; परख
v: searches | dhundhti; dhundhta; talaash; talash | ढूँढती; ढूंढती; ढूँढता; तलाश
v: finds | milti; milta; mil jaati; mil jaata; paati | मिलती; मिलता; मिल जाती; मिल जाता; पाती
v: learns | pata chalta; pata chalti; pata chal jaata; pata chal jaati; pata lagta | पता चलता; पता चल जाता; पता चल जाती
v: realises | ehsaas; ahsaas | एहसास; अहसास
v: decides | faisla | फ़ैसला; फैसला
v: asks | kehta; kehti; kehte; kehkar; kehna; kahti; kahta | कहता; कहती; कहते; कहकर; कहना
v: shouts at | chillata; chillati | चिल्लाता; चिल्लाती
v: helps | madad; sahayata | मदद; सहायता
v: rejects | thukra; thukrata; thukrati; thukra deta | ठुकरा; ठुकराता; ठुकराती; ठुकरा देता
v: dumps | thukra diya | ठुकरा दिया
v: refuses | mana kar; inkaar; inkar | मना कर; इनकार; इंकार
v: is escorted out | bahar nikaal diya jaata | बाहर निकाल दिया जाता
v: teaches | padhata; padhati; padhane; padhaata | पढ़ाता; पढ़ाती; पढ़ाने
v: works | kaam karne lagti; kaam karne lagta; kaam karti; kaam karta | काम करने लगती; काम करने लगता; काम करती; काम करता
v: scrubs | saaf karwati; saaf karwata; saaf karna | साफ़ करवाती; साफ करवाती; साफ़ करवाता
v: sells | bechti; bechta; bechna; beche | बेचती; बेचता; बेचना; बेचे
v: shows | dikhaati | दिखाती
v: buys | kharidti; kharidta; khareedna; kharid | खरीदती; खरीदता; खरीदने; खरीद
v: saves | bacha leta; bacha leti; bachata; bachati; bachane | बचा लेता; बचा लेती; बचाता; बचाती; बचाने
v: lives | rehti; rehta; rehte | रहती; रहता; रहते
v: chooses | chuni; chuna | चुनी; चुना
v: hides | chhupa li; chhupa liya; chhupati; chhupata; chhupa | छुपा ली; छुपा लिया; छुपाती; छुपाता; छिपा; छुपा
v: signs | sign karti; sign karta; dastakhat; dastkhat | साइन करती; साइन करता; दस्तख़त; दस्तखत
v: remarry | dobara shaadi; dobaara shaadi | दोबारा शादी
v: refuses to let him eat | saath khana khane se mana | साथ खाना खाने से मना
"""

# --------------------------------------------------------------------------------------------
_FUNC_DROP = "f"


def rkey(w: str) -> str:
    """Spelling-variant key for Roman-script Hindi: shaadi/shadi/shaaddi -> same key."""
    w = w.lower()
    w = w.replace("ee", "i").replace("ii", "i").replace("oo", "u").replace("uu", "u").replace("aa", "a")
    w = re.sub(r"(.)\1+", r"\1", w)
    w = re.sub(r"(?<![sc])h", "", w)        # drop h in kh/gh/dh/bh/th/ph/jh and final -h, keep sh/ch
    w = w.replace("w", "v").replace("z", "j").replace("q", "k")
    return w


def _norm_dev(w: str) -> str:
    # fold nukta forms and chandrabindu/anusvara variants so spelling variants meet
    for a, b in (("़", ""), ("ँ", "ं")):
        w = w.replace(a, b)
    return w


def _parse():
    roman: dict[tuple[str, ...], tuple[str, str]] = {}
    dev: dict[tuple[str, ...], tuple[str, str]] = {}
    for line in _RAW.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        kind = "n"
        if line.startswith("f:"):
            kind, line = "f", line[2:].strip()
        elif line.startswith("v:"):
            kind, line = "v", line[2:].strip()
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        english = parts[0]
        for variants, table, norm in ((parts[1], roman, lambda t: tuple(rkey(x) for x in t)),
                                      (parts[2] if len(parts) > 2 else "", dev, lambda t: tuple(_norm_dev(x) for x in t))):
            for v in variants.split(";"):
                toks = tuple(v.strip().split())
                if toks:
                    table.setdefault(norm(toks), (english, kind))
    return roman, dev


ROMAN, DEVANAGARI = _parse()
MAX_PHRASE = max(len(k) for k in list(ROMAN) + list(DEVANAGARI))
