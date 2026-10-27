# Policy di code review

## 1. Scopo

Questo documento definisce le regole per la revisione delle modifiche proposte nel *repository*.

L'obiettivo della *code review* è garantire la correttezza, la coerenza, la leggibilità e la manutenibilità dei contenuti, favorendo la collaborazione tra i membri del team e riducendo il rischio di introdurre errori nel *branch* `main`.

## 2. Ambito di applicazione

La code review si applica alle *Pull Request* che introducono modifiche al repository, inclusi:

- Documenti in formato Markdown e LaTeX.
- Verbali delle riunioni e documentazione relativa al progetto.
- File di configurazione e *workflow* GitHub Actions.
- Sito web e relativi file HTML e CSS.
- Altri materiali e strumenti di supporto presenti nel repository.

L'intensità della revisione deve essere proporzionata alla natura e alla complessità delle modifiche proposte.

## 3. Regole generali

Ogni Pull Request deve essere revisionata prima di essere integrata nel branch `main`.

La revisione deve essere effettuata da almeno un membro del team diverso dall'autore della Pull Request.

Il revisore deve esaminare le modifiche proposte con attenzione, verificando che siano coerenti con gli obiettivi dell'attività e con le convenzioni definite nei documenti organizzativi del repository.

L'autore è responsabile della qualità delle modifiche proposte e della gestione dei commenti ricevuti durante la revisione.

Non è consentito approvare una Pull Request senza averne verificato adeguatamente il contenuto.

## 4. Aspetti da verificare

Durante la code review devono essere considerati, quando pertinenti, i seguenti aspetti.

### 4.1. Correttezza e completezza

- Le modifiche soddisfano i requisiti dell'attività o dell'*issue* associata.
- I contenuti sono corretti, coerenti e sufficientemente completi.
- Non sono state introdotte informazioni contraddittorie o ridondanti.
- I riferimenti ad altri documenti, file e risorse sono corretti.

### 4.2. Qualità della documentazione

- Il testo è chiaro, comprensibile e grammaticalmente corretto.
- La terminologia è utilizzata in modo coerente.
- La struttura dei documenti è appropriata e facilita la consultazione.
- La formattazione rispetta le [convenzioni generali](formatting.md) e, per i documenti LaTeX, la struttura definita dai [template](../docs/tex/templates/), ove applicabili.

### 4.3. File tecnici e configurazioni

Quando la Pull Request riguarda file tecnici, il revisore deve verificare, per quanto applicabile:

- La correttezza delle modifiche ai file di configurazione.
- La coerenza dei workflow con le procedure del repository.
- L'assenza di errori evidenti nel codice HTML, CSS e LaTeX modificato.
- Il corretto funzionamento delle funzionalità interessate dalle modifiche.
- L'assenza di credenziali, *token* o altri dati riservati inseriti accidentalmente nei file.

### 4.4. Verifiche automatiche

Il revisore deve verificare che i controlli automatici previsti per la Pull Request siano stati completati con esito positivo.

Se un controllo fallisce, la causa deve essere esaminata e risolta prima del *merge*.

## 5. Gestione dei commenti

I commenti della code review devono essere chiari, pertinenti e, quando possibile, accompagnati da una proposta di miglioramento.

Per facilitare la gestione delle osservazioni, si distinguono due categorie:

- **Bloccanti**: segnalano problemi che devono essere risolti prima dell'approvazione o del merge, come errori sostanziali, requisiti non soddisfatti o malfunzionamenti.
- **Non bloccanti**: suggeriscono miglioramenti che non impediscono l'integrazione delle modifiche, come preferenze stilistiche o ottimizzazioni facoltative.

L'autore deve rispondere alle osservazioni ricevute e apportare le correzioni necessarie.

I commenti bloccanti devono essere risolti prima del merge e il revisore deve verificarne la risoluzione.

Per i commenti non bloccanti, l'autore e il revisore concordano se apportare le modifiche nella Pull Request corrente oppure registrarle per un'attività successiva. In quest'ultimo caso, le modifiche possono essere rinviate senza impedire il merge.

## 6. Approvazione e merge

Una Pull Request può essere integrata nel branch `main` quando sono soddisfatte tutte le seguenti condizioni:

- Ha ricevuto almeno un'approvazione da un membro del team diverso dall'autore.
- I controlli automatici obbligatori sono stati superati.
- Non presenta conflitti irrisolti con il branch di destinazione.
- Tutti i commenti bloccanti sono stati risolti.
- Le modifiche rispettano le convenzioni e le regole organizzative del repository.

L'integrazione deve avvenire secondo la strategia ***Standard merge***, come definito nella [strategia di *branching*](branching-strategy.md).

L'approvazione della Pull Request non sostituisce la responsabilità dell'autore di verificare la correttezza delle modifiche.

### 6.1. Approvazione dei documenti

Per le Pull Request che riguardano documenti soggetti ad approvazione, oltre ai criteri generali si applicano le seguenti regole.

Durante la redazione e la revisione, il documento deve mantenere lo stato **Bozza**. I campi relativi alla versione e alla data di approvazione devono rimanere vuoti (`-`) fino alla prima approvazione.

Al termine della revisione, il verificatore, che deve essere diverso dall'autore, procede in base all'esito della Pull Request:

- **Revisione non superata**: il verificatore non approva la Pull Request e richiede le correzioni necessarie. Aggiorna il registro delle modifiche assegnando la versione `0.1.0` al primo esito negativo oppure incrementando la versione preliminare precedente secondo le regole descritte di seguito. Il documento rimane in stato **Bozza**.
- **Revisione superata**: il verificatore approva la Pull Request e assegna la versione `1.0.0` alla prima approvazione oppure incrementa di uno il contatore più a sinistra rispetto all'ultima versione approvata, azzerando i due contatori successivi. Imposta lo stato su **Approvato** e completa i campi relativi alla versione e alla data di approvazione.

Le versioni seguono il formato `X.Y.Z`, secondo le seguenti regole:

- In caso di revisione non superata, il contatore più a destra (`Z`) viene incrementato di uno.
- Quando `Z` raggiunge `9`, l'incremento successivo lo riporta a `0` e incrementa di uno il contatore centrale (`Y`).
- In caso di revisione superata, il contatore più a sinistra (`X`) viene incrementato di uno rispetto all'ultima versione approvata, mentre `Y` e `Z` vengono azzerati.

Il registro delle modifiche deve riportare la versione e la data corrispondenti a ciascun esito della revisione. La versione approvata deve corrispondere al contenuto effettivamente revisionato e integrato nel repository.

Le modifiche successive a un documento già approvato devono essere sottoposte a una nuova Pull Request. L'aggiornamento della versione, dello stato, della data di approvazione e del registro delle modifiche deve essere verificato nell'ambito della revisione.

## 7. Nuove modifiche dopo l'approvazione

Se, dopo l'approvazione, vengono introdotte modifiche sostanziali alla Pull Request, il revisore deve verificare nuovamente le parti interessate.

## 8. Eccezioni

Eventuali eccezioni alla presente policy devono essere motivate e concordate dal team.

Le eccezioni non devono compromettere la qualità delle modifiche, la tracciabilità delle decisioni o la stabilità del branch `main`.

## 9. Revisione del documento

La presente policy può essere modificata tramite Pull Request quando emergono esigenze organizzative o tecniche che rendono necessario aggiornare le procedure di code review.