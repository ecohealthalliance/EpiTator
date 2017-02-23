#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the GeonameAnnotator that annotates a sentence with locations from
the Geonames dataset."""

import sys
import os
import unittest

sys.path = ['./'] + sys.path

from annotator.annotator import AnnoDoc
from annotator.geoname_annotator import GeonameAnnotator
from annotator.loader import HealthMapFileLoader
import logging
logging.getLogger('annotator.geoname_annotator').setLevel(logging.ERROR)

class GeonameAnnotatorTest(unittest.TestCase):


    def test_chicago(self):

        annotator = GeonameAnnotator()

        text = 'I went to Chicago.'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)
        self.assertEqual(len(doc.tiers['geonames'].spans), 1)
        self.assertEqual(doc.tiers['geonames'].spans[0].text, "Chicago")
        self.assertEqual(doc.tiers['geonames'].spans[0].label, "Chicago")
        self.assertEqual(doc.tiers['geonames'].spans[0].start, 10)
        self.assertEqual(doc.tiers['geonames'].spans[0].end, 17)

    def test_mulipart_names(self):

        annotator = GeonameAnnotator()

        text = 'I used to live in Seattle, WA'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)
        #print doc.tiers['geonames'].spans
        self.assertEqual(len(doc.tiers['geonames'].spans), 1)
        self.assertEqual(doc.tiers['geonames'].spans[0].text, "Seattle, WA")

    def test_mulipart_names3(self):

        annotator = GeonameAnnotator()

        text = 'England, France, Germany and Italy are countries in Eurpoe'
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

        self.assertEqual(doc.text, text)
        self.assertEqual([
            span.text
            for span in doc.tiers['geonames'].spans
        ], [
            'England', 'France', 'Germany', 'Italy'
        ])

    def test_bug_causing_sentence(self):
        text = u"""
        In late June 2012, an increase in cases of prolonged fever for ≥3 days
        was reported from the Vanimo General Hospital in
        Vanimo, Sandaun Province.
        """
        annotator = GeonameAnnotator()
        doc = AnnoDoc(text)
        doc.add_tier(annotator)

    def test_northeast(self):
        doc = AnnoDoc(u"""
         Instead, a novel virus was isolated from a patient’s blood. Since March 2010, there were frequent reports of a unique group of hospitalized patients who presented with clinical symptoms similar to those of SFTS in Central and Northeast China (Fig. 1). On the basis of data from a primary investigation in 2009, an enhanced surveillance was implement- ed in selected provinces in China to further in- vestigate the cause and epidemiologic character- istics of SFTS. Here we describe the discovery and characterization of a novel phlebovirus in the Bunyaviridae family, designated SFTS bunyavirus (SFTSV), which is associated with SFTS. We also discuss the clinical manifestations of SFTS and the epidemiologic investigations. Methods Case Definition and Surveillance Methods Since 2009, we have implemented an active sur- veillance program in selected areas in Hubei and Henan provinces to identify patients with SFTS. The syndrome was characterized by acute fever (temperatures of 38°C or more) and thrombocyto- penia (platelet count, <100,000 per cubic millime- ter) of unknown cause.2 We collected blood sam- ples from hospitalized patients whose symptoms fulfilled the criteria of the case definition. We excluded patients whose symptoms fit these crite- ria but who had other clinical or laboratory-con- firmed diagnoses. We defined a laboratory-confirmed case as meeting one or more of the following criteria: the isolation of SFTSV from the patient’s serum, the detection of SFTSV RNA in the patient’s se- rum during the acute phase of the illness, or the detection of seroconversion or an elevation by a factor of four in serum IgG antibodies against SFTSV on enzyme-linked immunosorbent assay (ELISA), indirect immunof luorescence assay, or neutralization testing in serum obtained during the convalescent phase. If possible, we collected serum samples within 2 weeks after the onset of fever and again during the convalescent phase. We also collected serum samples from 200 patient- matched healthy persons living in the same areas and during the same time period. The research protocol was approved by the human bioethics committee of the Chinese Center for Disease Con- trol and Prevention, and all participants provided written informed consent. Isolation of an Unknown Pathogen In June 2009, a blood sample in heparin antico- agulant was obtained on day 7 after the onset of illness from a patient from Xinyang City in Henan Province. Because the cause of the illness was un- known, we designed a strategy to isolate the patho- gen by inoculating multiple cell lines susceptible to both viral and rickettsial agents, including hu- man cell line HL60; animal cell lines DH82, L929, Vero, and Vero E6; and tick cell line ISE6. The pa- tient’s white cells were used to inoculate cell mono- layers. The cells were cultured at 37°C in a 5% carbon dioxide atmosphere with media changes twice a week. In 2010, we used a related strategy to isolate an additional 11 strains of the virus by inoculation of serum or homogenized white cells onto Vero cells. Electron Microscopy A DH82-cell monolayer that was infected with SFTSV in T25 flasks was fixed for transmission electron microscopy with Ito solution, as de- scribed previously.3 Ultrathin sections were cut on a Reichert–Leica Ultracut S ultramicrotome, stained with lead citrate and examined in a Phil- ips 201 or CM-100 electron microscope at 60 kV. Negative-stain electron microscopy was performed on virions purified from a clarified culture super- natant of infected Vero cells concentrated by a factor of 100.4,5 Genetic Analysis For the first SFTSV isolate, formalin-fixed cell cul- ture was used to extract viral RNA using a High Pure FFPE RNA Micro Kit (Roche Applied Sci- ence). The virus was sequenced with the use of the restriction-fragment–length-polymorphism assay with amplified complementary DNA, as described previously.6 For the remaining 11 strains of the virus, the whole genomes were sequenced with the use of the sequence-independent, single-primer amplification (SISPA) method.7 The 5' and 3' ter- minals of viral RNA segments were determined with a RACE Kit (Invitrogen). Phylogenetic analy- ses were performed with the neighbor-joining method with the use of the Poisson correction and complete deletion of gaps. Neutralization Assay For microneutralization testing, serial dilutions of serum samples were mixed with an equal vol- ume of 100 median tissue-culture infectious dos- es of SFTSV (strain HB29) and incubated at 37°C for 1.5 hours. The mixture was then added to a 96-well plate containing Vero cells in quadrupli- cate. The plates were incubated at 37°C in a 5% carbon dioxide atmosphere for 12 days. Viral in- fection was detected on specific immunofluores- cence assays in serum samples from patients with laboratory-confirmed infection. The end-point ti- ter was expressed as the reciprocal of the highest dilution of serum that prevented infection. Polymerase Chain Reaction RNA that was extracted from serum, whole blood, or homogenized arthropods was amplified with the use of a one-step, multiplex real-time reverse- transcriptase polymerase chain reaction (RT-PCR) with primers for SFTSV (Qiagen). The cutoff cycle- threshold value for a positive sample was set at 35 cycles. Nested RT-PCR and sequencing were used to verify samples from which only one ge- nomic segment was amplified. Virus Isolation The first SFTSV (strain DBM) was isolated from a 42-year-old man from Henan Province. A month after inoculation of cell monolayers with white cells obtained from the patient, virus-induced cellular changes visible on light microscopy (cyto- pathic effect) were observed in DH82 cells but not in the other cell lines. The morphologic features of infected DH82 cells changed from round mono- cytes to an elongated shape, which had granular particles in the cytoplasm (Fig. 2A). After several passages in culture, the cytopathic effect usually appeared on day 4 after inoculation of a fresh monolayer. Subsequently, 11 additional strains of the virus were isolated from serum samples ob- tained from patients during the acute phase of illness in six provinces with the use of Vero cells (Table 1 in the Supplementary Appendix, available with the full text of this article at NEJM.org). SFTSV can infect a variety of cells, including L929, Vero E6, Vero (Fig. 2B), and DH82 cells, but it re- sulted in the cytopathic effect only in DH82 cells. The viral particles were spheres with a diameter of 80 to 100 nm. Negative-stain electron microscopy of SFTSV particles that were purified from the su- pernatants of infected Vero cells revealed complex surface projections (Fig. 2C). Transmission electron microscopy revealed viral particles in the DH82-cell cytoplasm. The virions were observed inside vacu- oles, presumably in the Golgi apparatus (Fig. 2D). Partial sequences were obtained from the first isolated virus strain DBM, and the complete ge- nomes of 11 additional human isolates of SFTSV were determined. (GenBank accession numbers are provided in Table 1 in the Supplementary Ap- pendix.) All isolates including strain DBM were closely related (96% homology of nucleotide se- quences for all segments). The terminals of the three genomic segments of SFTSV were found to be similar to counterparts in other phlebovirus- es.8 The L segment contains 6368 nucleotides with one open reading frame encoding 2084 amino acids. The M segment contains 3378 nu- cleotides with one open reading frame encoding 1073 amino acid precursors of glycoproteins (Gn and Gc). The S segment contains 1744 nucleo- tides of ambisense RNA encoding two proteins, the N and NSs proteins, in opposite orientations, separated by a 62-bp intergenic region. Phylogenetic trees based on partial or complete viral genomic sequences of L, M, and S segments from strains DBM, HN6, and HB29 showed that SFTSV was related to prototypic viruses of the five genera of Bunyaviridae (Fig. 1 in the Supple- mentary Appendix). Among the genera orthobun- yavirus, hantavirus, nairovirus, phlebovirus, and tospovirus, SFTSV belongs to the phlebovirus genus8 but was more distantly related to proto- typic viruses in the other four genera. To verify this finding, we carried out a phylogenetic analy- sis, using complete deduced amino acid sequenc- es coding for RNA-dependent RNA polymerase, glycoproteins (Gn and Gc), and N and NSs pro- teins of SFTSV (strains HB29, HN6, AN12, LN2, JS3, and SD4) from six provinces in China, as com- pared with the other known phleboviruses (Fig. 3). The generated phylogenetic tree showed that all SFTSV isolates clustered together but were near- ly equidistant from the other two groups,9 the Sandfly fever group (Rift Valley fever virus, Punta Toro virus, Toscana virus, Massila virus, and Sandfly fever Sicilian virus) and the Uukuniemi group. This suggested that SFTSV is the proto- type of a third group in the phlebovirus genus. A comparison of the similarity of amino acid sequences provided further evidence that SFTSV is distinct from the other phleboviruses (Table 2 in the Supplementary Appendix). Both RNA- dependent RNA polymerase and glycoproteins of SFTSV are slightly more closely related to coun- terparts in Uukuniemi virus. However, N pro- teins in SFTSV and Rift Valley fever virus had 41.4% similarity. In contrast, the amino acids in NSs proteins encoded by the S segment showed a similarity of only 11.2 to 16.0% with amino acids in other phleboviruses. Serologic Analysis We evaluated seroconversion against SFTSV in pa- tients with SFTS using three different methods: immunof luorescence assay, ELISA, and microneu- tralization. We chose a cohort of 35 patients with RT-PCR–confirmed SFTSV infection who had se- rum samples from both acute and convalescent phases of the illness. An elevation in the anti- body titer by a factor of four or seroconversion was observed in all 35 patients, as seen especially on microneutralization (Table 1). These results indi- cated that high levels of neutralizing antibodies were generated during the convalescent phase of the illness. An antibody titer of more than 1:25,600 on ELISA was present in 15 convalescent-phase serum samples, indicating a robust humoral im- mune response against SFTSV. Among the 35 se- ropositive samples, all SFTSV infections were confirmed on viral RNA sequencing, and 11 were confirmed on virus isolation. It is noteworthy that specific neutralizing antibodies against SFTSV persisted in some convalescent-phase serum sam- ples even 1 year after recovery. Clinical Symptoms The first patient, a 42-year-old male farmer, pre- sented with fever (temperatures of 39.2 to 39.7°C), fatigue, conjunctival congestion, diarrhea, abdom- inal pain, leukocytopenia, thrombocytopenia, pro- teinuria, and hematuria. Later, a unique group of hospitalized patients with acute high fever with thrombocytopenia was identified. We analyzed only 81 patients with laboratory-confirmed SFTSV infection who had a complete medical record for the clinical spectrum of SFTS. The clinical symp- toms of SFTS were nonspecific, and the major symptoms included fever and gastrointestinal symptoms. Regional lymphadenopathy was also frequently observed (Table 2). The most common abnormalities on laboratory testing were thrombo- cytopenia (95%) and leukocytopenia (86%) (Table 3). Multiorgan failure developed rapidly in most patients, as shown by elevated levels of serum ala- nine aminotransferase, aspartate aminotransfer- ase, creatine kinase, and lactate dehydrogenase. Proteinuria (in 84% of patients) and hematuria (in 59%) were also observed. Among the 171 con- firmed cases, there were 21 deaths (12%). However, it is not clear how SFTSV caused these deaths. Epidemiologic Investigation From June 2009 through September 2010, we de- tected SFTS bunyavirus RNA, specific antiviral antibodies, or both in 171 patients among 241 hospitalized patients who met the case defini- tion for SFTS2 in Central and Northeast China. These patients included 43 in Henan, 52 in Hubei, 93 in Shandong, 31 in Anhui, 11 in Jiangsu, and 11 in Liaoning provinces. In 2010, a total of 148 of 154 laboratory-confirmed cases (96%) occurred from May to July. The ages of the patients ranged from 39 to 83 years, and 115 of 154 patients (75%) were over 50 years of age. Of these 154 patients, 86 (56%) were women, and 150 (97%) were farm- ers living in wooded and hilly areas and working in the fields before the onset of disease. No SFTSV was identified on real-time RT-PCR and no anti- bodies against SFTSV were identified in serum samples that were collected from 200 patient- matched healthy control subjects in the endemic areas, from 180 healthy subjects from nonendem- ic areas, and from 54 patients with suspected hem- orrhagic fever with renal syndrome. Mosquitoes and ticks were commonly found in the patients’ home environment. However, viral RNA was not detected in any of 5900 mosquitoes tested. On the other hand, 10 of 186 ticks (5.4%) of the species Haemaphysalis longicornis that were collected from domestic animals in the areas where the patients lived contained SFTSV RNA. The viruses in the ticks were isolated in Vero cell culture, and the RNA sequences of these viruses were very closely related but not identical to the SFTSV isolated in samples obtained from the patients (data not shown). There was no epidemiologic evidence of human-to-human transmission of the virus. Discussion Although we have not fulfilled Koch’s postulates for establishing a causal relationship between a mi- crobe and a disease in their entirety, our findings suggest that SFTS is caused by a newly identified bunyavirus. These data include epidemiologic, clinical, and laboratory findings and several lines of evidence that include virus isolation, viral RNA detection, and molecular and serologic analyses. SFTS has been identified in Central and Northeast China, which covers all six provinces where sur- veillance for SFTS was carried out.
         """)
        doc.add_tier(GeonameAnnotator())
        self.assertTrue(
            'Northeast' not in [span.text for span in doc.tiers['geonames'].spans]
        )

    def test_adjacent_state_name(self):
        text = """3 at Washington County [Pennsylvania] Shelter Treated For Rabies Exposure"""

        # TODO Make sure this is Washington County PA, not OR


    def test_url_names(self):
        doc = AnnoDoc(u"""
        [1] Cholera - South Sudan
        Date: 19 Jul 2014
        Source: Radio Tamazuj [edited]
        https://radiotamazuj.org/en/article/south-sudan-100-total-cholera-deaths
        """)
        doc.add_tier(GeonameAnnotator())
        print doc.tiers['geonames']
        self.assertEqual(len(doc.tiers['geonames']), 1)

    def test_for_duplicate_spans(self):
        doc = AnnoDoc(u"""
        Hidalgo in the Tezontle in Pachuca 3 in Tlaxcoapan, 4 in Mixquiahuala and 4 in Tetepango.

        175 cases of cholera were confirmed in La Huasteca (159 in Hidalgo, 14 in Veracruz, and 2 in San Luis Potosi) in La Huasteca area (http://en.wikipedia.org/wiki/La_Huasteca), a geographical and cultural region located in Mexico along the Gulf of Mexico that includes parts of the states of Tamaulipas, Veracruz, Puebla, Hidalgo, San Luis Potosi, Queretaro, and Guanajuato
        """)
        doc.add_tier(GeonameAnnotator())
        duplicate_spans = []
        span_starts = set()
        for span in doc.tiers['geonames'].spans:
            if span.start in span_starts:
                duplicate_spans.append(span)
            span_starts.add(span.start)
        self.assertEqual([unicode(s) for s in duplicate_spans], [])

    def test_parent_cycles(self):
        doc = AnnoDoc(u"""
        California National Primate Research Center (CNPRC).
        (University of California, San Francisco)
        Koch’s postulates
        The University of California, Davis
        and University of California, San Francisco
        Sera from the Blood Systems Research Institute (San Francisco, CA)
        in California (Blood Centers of the Pacific, San Francisco, CA), Nevada
        (United Blood Service, Reno, NV),
        and Wyoming (United Blood Services, Cheyenne, Wyoming)
        The California National Primate Research Center (CNPRC)
        personal protective equipment (PPE) policy
        (Focus Diagnostics, Cypress, CA).
        """)
        doc.add_tier(GeonameAnnotator())
        for span in doc.tiers['geonames'].spans:
            if 'parent_location' in span.geoname:
                self.assertNotEqual(
                    span.geoname['parent_location'],
                    span.geoname['parent_location']\
                        .get('parent_location',{})\
                        .get('parent_location'))
            if span.geoname['name'] == 'Reno':
                self.assertEqual(
                    span.geoname['parent_location']['name'], 'Nevada')

if __name__ == '__main__':
    unittest.main()
