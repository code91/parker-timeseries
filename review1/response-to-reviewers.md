# Response to the Editors and Reviewers

**Manuscript:** "Bird" Over Time: A Time Series Analysis of Charlie Parker's Harmonic Complexity
**Author:** Michele "Mike" Rubini
**Journal:** Empirical Musicology Review

---

We thank the Editors-in-Chief and both reviewers for reports that were detailed, fair and, in several places, correct about things we had got wrong. Every point raised is addressed below, with the location of each change.

Four of the changes go beyond editing, and we flag them at the outset because they alter what the paper claims.

**1. We ran the control analysis Reviewer 1 proposed, and withdrew a claim as a result.** Reviewer 1 asked whether the temporal structure we report might belong to the chord progressions rather than to Parker, and suggested generating interval vectors from chord-scale theory as a baseline. We built that null model (new §Robustness checks; new Table 4). It holds the progressions, keys, phrase boundaries and positions fixed and replaces the improviser, across 500 simulated corpora. Two findings survive: phrase-to-phrase predictability (lag-1 autocorrelation +0.152 observed against −0.031 null) and the Dissonance→Complexity effect (17.4% against 4.8%, 95% interval [0.0, 13.0]). One does not: the Complexity→Dissonance rate (8.7% against 4.9%, interval [0.0, 12.0]) lies inside the null, and **we have withdrawn that claim**. The directional asymmetry is now reported as one direction that survives the control and one that does not.

**2. We tested the collinearity Reviewer 1 suspected, and it is severe.** Dissonance is a weighted sub-sum of the same six numbers complexity totals, and the two correlate at *r* = .94. Every Granger test was re-run with a density-independent dissonance (dissonance ÷ complexity, *r* = .03 with complexity). The pattern is unchanged and slightly strengthened: 84.8% of tunes show no relation either way, against 80.4% before. Both sets of figures are now reported (new Table 5).

**3. We report the ANOVA assumption checks Reviewer 2 recommended, and both assumptions fail.** Variances differ across frequency quartiles (Levene *W* = 7.28, *p* < .001) and no quartile is normally distributed (Shapiro–Wilk *p* < .05 in all four). The finding survives without the assumptions and is in fact stronger: Kruskal–Wallis *H*(3) = 30.50, *p* < .001, and Spearman ρ = −.47 against the Pearson −.35.

**4. We state a property of the complexity measure that the paper had left implicit.** Complexity equals *n*(*n*−1)/2 in the number of distinct pitch classes, exactly, in all 3,371 segments. It is a re-expression of distinct-pitch-class count and carries no information about which classes are used. This is now stated where the measure is defined, and it answers Reviewer 1's question about what the sum of an interval vector means.

We also corrected two errors of our own that the reviews led us to: a mislabelled confidence interval, and a miscounted triad in a worked example. Both are described in context below.

---

## Part 1. Editors' requested changes

**E1. Resubmit using the EMR template, with APA 7 structure and headings.**
The manuscript is now built directly on `EMR_article_template2020.docx` and inherits its styles rather than imitating them. Verified against the template: page size and margins, header and footer, the three heading levels, 16 pt bold title, 10 pt upper-case author line, 10 pt italic affiliation, opening word in upper case with a 12 pt initial letter, 0.5 in paragraph indent, figure captions below figures with a bold "Fig. N.", table headings above tables, endnotes rather than footnotes, and American spellings. Tables, table notes and captions are set in the body font of 10 pt, per the template's instruction that "Tables, table captions and figure captions are in the same font as regular text". The abstract is block indented to 4.45 cm (1.75 in) from the page edge, matching the template's own abstract paragraph, and has been shortened to 189 words, within the 200-word limit. Keywords are italicised.

**E2. Refer explicitly to every figure and table in the main text.**
All 14 figures and all 6 tables are now cited in the text. Figure 3 of the original submission has been removed (see E8).

**E3. Expand the Introduction; the reference list is too brief.**
The Introduction has been rewritten and now surveys four literatures: the analytical tradition on Parker (Owens, Martin 1996 and 2020, Love), cognitive accounts of improvisation (Pressing, Johnson-Laird, Berkowitz, Norgaard, Norgaard et al., Goldman), computational corpus study (the Jazzomat project, Broze and Shanahan, Merseal et al., Riley and Dixon), and formalizations of harmonic complexity (Forte, Lerdahl, Farbood, Plomp and Levelt, Sethares). The reference list has grown from 9 entries to 29, and all 29 are cited in the text.

**E4. Make the text accessible to an interdisciplinary reader; define "interval class" and "trap-door structure" at first use; introduce Parker.**
Parker is introduced on first mention as "Charlie Parker (1920–1955), the alto saxophonist whose playing did more than any other to establish the bebop idiom of the 1940s". A terminology section in the Introduction now defines interval class, interval vector, segment, complexity, dissonance, rate of change and triadic content before any of them is used. Trap-door structure is defined at first use and explicitly marked as our own term, not a standard one. The further concepts Reviewer 2 listed are addressed in Part 3.

**E5. Paragraph 2, p. 9: six specific problems.**
*(i) The inference from tonic function.* The claim no longer rests on the frequency table. We now test it directly: complexity is higher over tonic chords (*M* = 10.85) than over other functions pooled (*M* = 9.66), reliable at this corpus size (Kruskal–Wallis *H* = 38.76, *p* < .001) but small (Cohen's *d* = 0.17). We also give the base rate: the top ten vectors fall on tonic chords in 29.3% of their occurrences against a corpus-wide 30.6%, so the function distributions reflect the prevalence of tonic harmony rather than a preference. The conclusion is now stated as a modest shift, not a categorical distinction.
*(ii) "{C, D, E♭, B♭}" omitting the third.* The reviewer is right that this reads as a Cm9. The passage has been rewritten. (122010) is now correctly identified as Forte 4-10, prime form [0,2,3,5], and described through its three commonest realizations above the sounding root, of which {root, 5, 13, ♭7} is the one omitting the third; 46.0% of all occurrences of the vector contain no third of any kind.
*(iii) "(root, 9, 9, ♭7)".* Corrected; the erroneous figure is gone with the rewritten passage.
*(iv) The unclear final sentence.* Rewritten.
*(v) (111000) → (111000) as a chord change.* We checked this directly rather than assuming it: 17 of those 18 transitions cross a change of chord symbol and only one stays on the same chord; corpus-wide, 83 of 112 same-vector transitions (74.1%) span an actual chord change. The text now reports this.
*(vi) The three means in §4.11.* Each is now defined before use: the unweighted mean over the 165 distinct vectors, the frequency-weighted mean (equivalent to the expected triadic content of a randomly drawn segment), and the comparison mean over the 145 vectors outside the top 20. We also explain the conceptual difference, namely what the vocabulary contains versus what a listener hears, and note that the gap between them is itself the finding.

**E6. Motivate the four Granger hypotheses.**
The Granger section now opens with the tension that motivates testing directional effects at all: pattern-retrieval accounts predict local reactive dependency, while thematic and schema-based accounts predict weak phrase-to-phrase dependency. Each of the four hypotheses is given its rationale and what support for it would imply. We note that no prior study has tested directional dependency between harmonic dimensions within improvised solos, and cite the related precedent in Broze and Shanahan, and in Chang et al. for the use of Granger causality in music.

**E7. Explain how harmonic segments are identified, with replication-level detail.**
A new Segmentation subsection specifies the unit in full: a segment is the span of a single chord symbol as annotated in the MusicXML, boundaries are given by the annotation rather than inferred, every notated pitch whose onset falls in the span is reduced to a pitch class, rests contribute nothing, and segments with fewer than three distinct pitch classes are dropped rather than merged. Descriptives are given for replication: 3,371 segments, median 61.5 per tune (range 32–122), median onset interval 2,000 ms, median 6 notated pitches reducing to 4 distinct pitch classes, 52.8% containing 3 or 4. Two consequences are stated plainly: segment length varies with the form, and a segment records which pitch classes were visited, not their order.

**E8. Delete the repeated "This yielded 1,507 phrases…" sentence on p. 6.**
Deleted. The phrase appears once.

**E9. Figures and tables.**
*Table 1 columns.* Forte class and proportion of the corpus are now columns in Table 1, with a note that Forte classes are given without inversional suffix and that percentages are of all 3,371 segments.
*Figure 5 and the median.* The reviewer is right that the distributions are skewed. We now lead with the median (6.0, IQR [6, 15]) and say explicitly that it is the more representative summary, retaining the mean only where needed for comparison with variance-based statistics. Medians are reported alongside means throughout the section.
*Figure 6.* It is a corpus-level statistic, not a single song, and the text now says so and explains the computation: chorus numbers are assigned per tune by dividing measure position by form length (12 bars for blues, 32 otherwise), distinct vectors in each chorus position are pooled across the 46 MIDI-aligned tunes, and coverage is accumulated.
*Cluster numbering.* Clusters 0–3 are gone. The groups are Strategies 1, 2 and 3 plus a single outlier tune, numbered consistently in text, figures and captions, with a note explaining that k-means labels arbitrarily from 0 and that we renumber by corpus prevalence. No cluster index appears anywhere in the article.

**E10. Figure files at 300 dpi in JPG or TIFF.**
Supplied separately as `Figure_01`–`Figure_14` in both TIFF (LZW) and JPEG, at 324–546 dpi, with a caption sheet. Four figures fell below 300 dpi at their printed size and were re-rendered from source rather than upscaled: the two pipeline diagrams from their HTML, the notated examples from MusicXML, and the robustness scatter redrawn from the analysis data.

---

## Part 2. Reviewer 1

We are grateful for this report. Its central methodological worry led to the new control analysis, and its question about correlated metrics led to the collinearity re-run; both are summarised above.

### Major points

**R1.1. Interval vectors discard ordering, frequency, contour, register, and metric placement. What is the advantage? Two licks with the same vector may not be the same thing.**
We accept the example and have stated the cost rather than minimised it. The Introduction now lists what the representation discards, including metric placement, and justifies the choice: the vector gives a single scalar description of each chord span that is comparable across tunes in different keys and at different tempos, which is what makes a time series treatment possible; melodic n-gram methods, which retain ordering, are correspondingly harder to compare across harmonic contexts. The Limitations state that a line with its dissonances on strong beats is heard differently from one where they pass between them, and that our measures cannot separate the two. The Discussion adds the related caveat that interval vectors are analysts' constructs: a regularity in them constrains theories of what Parker stored without identifying the stored objects, which the pattern literature suggests were melodic figures.

**R1.2. Phrase-boundary detection: are there counterexamples where it goes wrong?**
Yes, and both failure modes are now quantified in the text. A phrase can run on: the longest in the corpus spans twelve segments across measures 42–48 of "Kim (No. 1)", about seven bars with no notated rest of an eighth note or longer, which contains more than one gesture on any reading; four further phrases span ten segments. A boundary can also be spurious: 36.4% of all 1,507 boundaries come from a rest of exactly the 0.5-quarter threshold, so raising the threshold to one quarter note would dissolve more than a third of the phrases. We note that detection is least reliable at the extremes, and that the rolling-window analyses are correspondingly less exposed to this than the phrase-level tests.

**R1.3. The dissonance weighting is arbitrary; show the evidence that alternatives give similar findings.**
The manuscript previously asserted this without support. We now test it. Clustering was repeated from scratch under five alternative weighting schemes; the strategy assignment is identical in three and agrees on 83–85% of tunes in the other two (new Table 3). We report that two schemes do move a handful of tunes, so the grouping is robust to the weighting without being wholly independent of it.

**R1.4. What does the sum of an interval vector mean? Wouldn't a chromatic scale score highly?**
It would, and the measure is now characterised exactly. Complexity equals *n*(*n*−1)/2 in the number of distinct pitch classes, with no exceptions across 3,371 segments, so it measures how much distinct pitch material is used over a chord and not how unusual that material is. The text says so where the measure is defined, and notes that a chromatic run scores highly while being, by other measures such as interval entropy, highly predictable.

**R1.5. The distance metric treats all changes as equivalent.**
Conceded in the text. The Methodology now states that replacing a tritone with a perfect fifth and a major second with a minor third register as the same distance although a listener would not hear them as equally large moves, and explains why we nonetheless use the measure: it is symmetric, requires no further weighting decisions, and is interpretable as motion in the space the vectors occupy. A perceptually weighted distance is named as a worthwhile refinement.

**R1.6. How correlated are the metrics, and what does that do to the causality analysis?**
This was the sharpest point in either report and the reviewer was right. The dependence is structural, not incidental. See item 2 of the summary above: *r* = .94, re-run with a density-independent measure, conclusions unchanged and slightly strengthened, both sets of figures reported.

**R1.7. How much do the chord changes themselves govern complexity and dissonance? A control analysis could settle it.**
Built, as proposed. See item 1 of the summary above, including the claim we withdrew as a result. The Limitations also note what the control does not do: it samples uniformly from one scale per chord function, where a player chooses unevenly within a scale and sometimes outside it, so it is a conservative floor rather than a model of how anyone improvises. Comparing performers on the same tune is named as the human-baseline successor to it.

**R1.8. Better contextualisation in the literature on the cognition of improvisation; the purpose risks getting lost.**
The Introduction now engages that literature directly (Pressing, Johnson-Laird, Berkowitz, Norgaard, Norgaard et al., Goldman) and states what the time series approach is for. A new Discussion section, *Relation to Earlier Findings*, compares our results with Frieler et al. (2016a) on solo dramaturgy and with Love (2012, 2017), noting where we converge and where the accounts make opposite predictions.

### Minor points

**R1.9. Why combine XML and MIDI, if segmentation is from rests?** The Methodology now separates the roles: MusicXML supplies pitches and notated rests, which define phrase boundaries; MIDI alignment supplies elapsed time, needed to index the series by real time for comparability across tempos and to report durations. We state plainly that real time is not needed for segmentation itself.
**R1.10. Use equation objects.** The three metric definitions are now display equations set as equation objects.
**R1.11. Figure 4: "match rests to harmonic segments" is unclear.** The diagram has been re-rendered; that step now reads "Locate Each Rest in the Segment Sequence", with the fallback order spelled out in words.
**R1.12. Is a 6-phrase minimum enough?** Described honestly as a floor rather than an adequacy threshold: a lag-5 autocorrelation cannot be computed on a shorter series, estimates from six observations are themselves imprecise, and the figure is low only because raising it would discard tunes. In practice the constraint rarely binds, as the median tune contributes 32.8 phrases. The Granger tests use a stricter minimum of 10.
**R1.13. Was PCA part of the pipeline?** Clarified: principal components were used only to inspect cluster separation visually, not as an analysis step.
**R1.14. The silhouette scores are not high.** Addressed directly rather than defended: such values are expected when the structure is a continuum rather than discrete kinds; the partition is stable under perturbation of the dissonance weights; and the groups predict Granger results they were not fitted on. We state that we treat the strategies as a useful description, not as evidence of discrete types.
**R1.15. Figure 10: what are the numbers on the x axis?** The caption now says the horizontal axis indexes tunes and carries no further meaning.
**R1.16. "Predictable unpredictability".** Removed and replaced with a plain statement.
**R1.17. "Tonic function", and what is a "II" function?** A note in Results explains that the labels are scale-degree positions taken from the corpus annotations, not the three-way tonic/predominant/dominant taxonomy, and that "II" would count as predominant in that taxonomy.
**R1.18. Figure 6: the long flat stretches.** Explained in the caption: each step adds only vectors not already seen, so once the common vocabulary has appeared most later segments contribute nothing new.
**R1.19. Claims about Pressing and Johnson-Laird assume interval vectors are part of Parker's vocabulary.** Addressed by the caveat described under R1.1, and by the attribution corrections under R2 below.
**R1.20. Future directions should be elaborated.** Expanded with three concrete programmes: dating the corpus to test for change across Parker's career, the human-baseline control, and perceptual validation of the measures.

---

## Part 3. Reviewer 2

We thank the reviewer for a recommendation of minor revisions and for a list of specific, actionable items. Nearly all have been adopted verbatim.

### Content and argument

**R2.1. Many key concepts are undefined or vaguely defined.**
A terminology section now defines the core measures before use (see E4). Of the eighteen concepts listed: *harmonic content*, *harmonic material*, *pitch-class density*, *temporal granularity*, *surface articulation*, *PCA space* and *positional centrality* have been removed from the manuscript entirely, replaced by plainer wording; *harmonic complexity*, *segment*, *rate of change*, *triadic content*, *triadic sparsity*, *reactive navigation*, *perceptual roughness*, *sensory dissonance* and *tonal dissonance* are now defined at first use. We also adopted the reviewer's point about using one term rather than two: "harmonic segment" is now simply "segment" throughout, "variability" has given way to "volatility", and "harmonic complexity" is reserved for the research literature on that construct rather than our own measure.

**R2.2. Explain how interval analysis measures harmonic complexity; distinguish harmonic from melodic complexity; explain sensory and tonal dissonance; spell out IV at first use.**
All adopted. The terminology section spells out interval vector (IV) at first mention. Sensory dissonance (critical-band roughness, a property of the sound) and tonal dissonance (instability within a key, context-dependent) are now distinguished explicitly, with a statement that our weighting captures the first and not the second because no vertical sonority is sounded. A worked example computes an interval vector from four notes over a C7, step by step.

**R2.3. Explain how the dissonance–complexity relationship licenses conclusions about chorus-level planning versus reactive navigation; define reactive navigation.**
The Granger section now sets out the two competing accounts and the opposite predictions they make, states that they are distinguished by the overall rate of significant effects rather than any single test, and defines reactive navigation as a performer responding to the conditions created by the phrase just played.

**R2.4. ANOVA with time-ordered data; report assumption checks.**
Done, and both assumptions fail. See item 3 of the summary above. Gorman and Allison (1996) and Matyas and Greenwood (1996) are cited, as the reviewer suggested.

**R2.5. The Omnibook transcriptions contain errors; Van Bebber reports correcting over a thousand.**
Added to the Limitations, with the attribution. We note that errors at that rate will add noise to every measure, that they are unlikely to be systematic with respect to position in a performance and so unlikely to generate the temporal patterns we report, but that they will attenuate real effects. Slone and Aebersold (1978) are now cited as the source of the transcriptions, alongside Déguernel et al. for the encoding and Riley and Dixon for the alignment.

### Writing style, figures, formatting

**R2.6. Reduce the number of figures or move most to an appendix.**
The manuscript had 14 figures; it now has 14, of which four sit in an appendix and one of the originals was removed. The principle we applied is that a figure stays in the body when it is the only evidence for a claim the body makes, and moves to the appendix when it duplicates a schematic, a number already printed, or another figure. On that basis the appendix takes the analysis-pipeline schematic, the cross-chorus comparison (which restated three numbers already given in a list), the per-tune head-versus-chorus scatter, and the autocorrelation profiles.

**R2.7. APA p-values and APA reference style.**
All p-values are reported without a leading zero, with *p* < .001 as the floor. The reference list is alphabetical and APA-formatted, with sentence-case titles. The reviewer's three specific corrections (Déguernel et al., Merseal et al., Riley and Dixon) were applied as given. We also checked every entry: all 29 are cited in the text, and none needs removing.

### Page-by-page comments

All of the following were adopted as suggested: replacing "composed melodies and improvisations" with "composed melodies and solos"; replacing "Bridge sections (bars 17–24 in AABA)" with "(B in AABA)"; lower-casing "BUILD-SUSTAIN" and explaining what build-sustain and build-decay mean; replacing "Cross-chorus analysis" with "Chorus-level analysis"; simplifying the rolling-window passage to "For each window, we calculated mean, standard deviation, and coefficient of variation"; defining volatility and explaining what a centered window is and why; clarifying what each clustering feature measures; describing each strategy where it is first introduced rather than only in a figure caption; replacing "we aggregated segment-level metrics into phrase-level statistics" with "we calculated"; rewriting "heads contain most vocabulary"; removing "performer-general"; simplifying the sentence about navigational options and network position; adding a parenthesis to the rate-of-change mean; and reporting "frequency of interval vectors and triadic content" rather than "frequency and triadic content".

Four comments deserve individual replies.

**R2.8. The abstract's second paragraph is hard to follow, and uses labels without explaining them.**
Rewritten in plainer language, with each strategy label given its meaning in context. The abstract is now 189 words, within the 200-word limit; the previous version was 257 words and over it, which we had not noticed.

**R2.9. Figure 3 is probably reprinted from the Omnibook and would need permission.**
The reviewer is right and we have removed the figure. As the reviewer notes, phrase detection is adequately described in prose. The notated examples that now appear (Figure 3 in the revised manuscript) are our own, engraved from scratch, and reproduce nothing from the Omnibook.

**R2.10. The contrafact explanation does not account for heads being less complex; some heads contain improvised B-sections, and some recordings have no pre-composed head.**
Accepted in full. The text now concedes that borrowing a progression says nothing about the density of the melody written over it, keeps the melodic-memorability explanation as the actual proposal, and adds both of the reviewer's cases, citing Yamaguchi (2012) on "Bird of Paradise". We note that both import solo material into the head category and would therefore narrow the difference we report rather than produce it.

**R2.11. The Cohen's *d* value is not within the confidence interval.**
The reviewer is right that *d* = −0.87 lies outside [−2.55, −1.50]. The numbers are correct but the label was wrong: the interval belongs to the difference in means (2.0 triads), not to *d*. It is now reported as such. We are grateful for the catch.

**R2.12. Avoid "causal", "causality" and "causal relationship" when reporting Granger results.**
Adopted throughout. The manuscript now says that one series Granger-causes another, and reserves "cause" and "causality" for the method's name. *Gravity* is retained as the name of the concept but is defined in predictive terms: the extent to which one quantity helps predict another one phrase later, beyond what that quantity's own past predicts. The phrase "composed improvisation" has been removed in favour of "chorus-level architectural planning", as the reviewer suggested, to avoid invoking the composition/improvisation debate.

**R2.13. Are the Pressing and Johnson-Laird citations correct?**
The reviewer was right to query both. The Pressing passage has been rewritten to drop the claim that he identifies event clusters as cognitive bottlenecks, and now rests only on the general claim that processing load varies across a performance. Johnson-Laird's "algorithmic" and "inspirational" labels are now explicitly marked as ours, introduced for brevity, rather than attributed to him.

**R2.14. Recording dates and possible change across Parker's career.**
Added to Future Directions, with the Dig That Lick metadata collection named as the source that would make it possible.

---

## Errors we found and corrected

Beyond the points raised, two errors came to light while responding and are corrected in the revised manuscript.

**A miscounted triad.** The text stated that {C, E, G, B♭} contains one complete triad, C major. It contains two: C major and E diminished. The sparse example has been replaced with {C, D, E♭, B♭}, which genuinely contains none, so the contrast now runs none / two / four and is shown in notation.

**An unreproducible analysis.** The robustness results could not be regenerated from the public repository, because the committed time series holds only the MIDI-aligned subset while those results are computed over the full corpus, and the intermediate file the script reads was excluded by `.gitignore`. That file has been rebuilt from data already in the repository, verified to reproduce every published figure exactly, and committed. The analysis is now reproducible as the paper claims.

---

We hope these revisions meet the Editors' and reviewers' concerns. We are particularly grateful for the two methodological challenges that led us to run new analyses; the paper is more cautious and, we think, more convincing for them.
