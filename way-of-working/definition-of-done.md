# Definition of Done

## 1. Scopo

Questo documento definisce i criteri minimi che un'attività deve soddisfare per essere considerata completata.

L'obiettivo è garantire che le modifiche introdotte nella *repository* siano corrette, complete, coerenti con le convenzioni del team e pronte per essere integrate nel branch principale.

## 2. Ambito di applicazione

La *Definition of Done* si applica alle attività che comportano modifiche alla repository, tra cui:

- Documentazione in formato Markdown e LaTeX.
- Verbali delle riunioni e materiali relativi alla candidatura.
- File di configurazione e *workflow* GitHub Actions.
- Sito web e relativi file HTML e CSS.
- Altri materiali e strumenti di supporto presenti nella repository.

I criteri devono essere applicati in modo proporzionato alla natura dell'attività e alle modifiche introdotte.

## 3. Criteri di completamento

Un'attività può essere considerata completata quando soddisfa tutti i criteri applicabili tra quelli seguenti.

### 3.1. Requisiti e contenuti

- Le modifiche soddisfano gli obiettivi e i requisiti dell'attività o dell'issue associata.
- I contenuti sono corretti, completi e coerenti con il contesto.
- Non sono presenti informazioni contraddittorie o ridondanti che compromettano la comprensione.
- I riferimenti a file, documenti e risorse sono corretti.

### 3.2. Qualità e formattazione

- I contenuti sono chiari, comprensibili e coerenti dal punto di vista terminologico.
- Sono rispettate le convenzione adottate per la [struttura]() e la formattazione.
- I documenti LaTeX utilizzano i template e le configurazioni condivise, ove applicabili.
- Le modifiche mantengono la coerenza con gli altri documenti e materiali della repository.

### 3.3. Verifiche tecniche

Quando applicabile, devono essere effettuate le verifiche necessarie per accertare la correttezza delle modifiche:

- I documenti LaTeX interessati vengono compilati correttamente.
- I collegamenti e i riferimenti modificati risultano validi.
- Le modifiche al sito web vengono verificate per accertare il corretto funzionamento e la corretta visualizzazione dei contenuti interessati.
- I file di configurazione e i workflow modificati non presentano errori evidenti.
- I controlli automatici previsti per la Pull Request terminano con esito positivo.

Le verifiche non applicabili alla natura dell'attività possono essere omesse.

### 3.4. Versionamento e tracciabilità

- Le modifiche sono state apportate su un branch dedicato all'attività, secondo la [strategia di branching](branching-strategy.md).
- I commit rispettano le convenzioni definite in [commit-guidelines.md](commit-guidelines.md).
- L'issue associata, se presente, è aggiornata e correttamente referenziata.
- Le modifiche sono raccolte in una Pull Request descrittiva e coerente con l'attività svolta.

### 3.5. Revisione e integrazione

- La Pull Request è stata revisionata secondo la [policy di code review](code-review-policy.md).
- È stata ottenuta almeno un'approvazione da un membro del team diverso dall'autore.
- I commenti bloccanti sono stati risolti.
- I controlli automatici obbligatori sono stati superati.
- Non sono presenti conflitti irrisolti con il branch di destinazione.

## 4. Responsabilità

L'autore dell'attività è responsabile di verificare che i criteri applicabili siano soddisfatti prima di richiedere l'integrazione delle modifiche.

Il revisore verifica il rispetto dei criteri durante la code review, segnalando eventuali problemi che devono essere risolti prima del merge.

Il completamento dell'attività deve essere valutato sulla base dei criteri applicabili e delle verifiche effettivamente svolte.

## 5. Eccezioni

Eventuali deroghe ai criteri di completamento devono essere motivate e concordate dal team.

Le eccezioni devono essere limitate ai criteri non applicabili o ai casi in cui sia stata concordata una soluzione alternativa adeguata, senza compromettere la correttezza e la qualità delle modifiche.

## 6. Revisione del documento

La presente Definition of Done può essere aggiornata tramite Pull Request quando emergono nuove esigenze organizzative o tecniche o quando cambiano le procedure adottate dal team.