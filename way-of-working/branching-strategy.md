# Strategia di branching

## 1. Scopo

Questo documento definisce la strategia di *branching* adottata dal team per gestire lo sviluppo, la correzione e la manutenzione della parte documentativa del progetto.

L'obiettivo è mantenere una cronologia Git leggibile, facilitare la collaborazione e garantire che le modifiche siano revisionate prima di essere integrate nel *branch* principale.

## 2. Branch principale

Il branch `main` rappresenta la versione principale della *repository*.

Le seguenti regole si applicano a `main`:

- Deve contenere modifiche revisionate e approvate.
- Non è consentito effettuare *push* diretti, salvo eccezioni esplicitamente concordate dal team.
- Le modifiche devono essere integrate tramite *Pull Request*.
- Le [verifiche automatiche](../.github/workflows/) previste dal repository devono essere superate prima del *merge*.

## 3. Creazione dei branch

Ogni attività che comporta una modifica al repository deve essere sviluppata su un branch dedicato, creato a partire da `main` aggiornato.

I nomi dei branch devono essere descrittivi, brevi e scritti in minuscolo. Le parole devono essere separate da trattini (`-`).

Il formato da seguire è:

`<tipo>/<numero-issue>-<descrizione>`

I tipi di branch previsti sono:

| Tipo | Utilizzo | Esempio |
|---|---|---|
| `admin/` | Attività di amministrazione | `admin/12-workflow-compilazione-tex` |
| `docs/` | Attività di documentazione | `docs/24-aggiornamento-readme` |
| `website/` | Sviluppo sito web | `website/35-modifica-etichetta-proponente` |

Il numero dell'*issue* deve essere incluso quando l'attività è associata a un'issue GitHub. Per attività minori non associate a un'issue, il numero può essere omesso.

## 4. Flusso di lavoro

Il flusso di lavoro standard è il seguente:

1. Identificare o creare un'issue che descriva l'attività.
2. Aggiornare il branch locale `main`.
3. Creare un branch dedicato all'attività.
4. Implementare le modifiche ed eseguire le verifiche pertinenti.
5. Registrare le modifiche tramite *commit* conformi alle [convenzioni del repository](commit-guidelines.md).
6. Aprire una Pull Request verso `main`.
7. Attendere la revisione e il completamento dei controlli automatici.
8. Integrare le modifiche dopo aver soddisfatto i requisiti di approvazione.
9. Eliminare il branch di lavoro dopo il merge, salvo necessità di conservarlo per motivi specifici.

## 5. Aggiornamento dei branch

Durante lo sviluppo, è responsabilità dell'autore verificare che le modifiche rimangano compatibili con gli aggiornamenti del branch `main`.

Quando necessario, il branch di lavoro deve essere aggiornato con le modifiche più recenti di `main`, utilizzando le modalità concordate dal team.

Eventuali conflitti devono essere risolti e verificati dall'autore prima di richiedere il merge.

Non devono essere integrate modifiche che introducano conflitti irrisolti o compromettano la correttezza e la coerenza dei contenuti e dei materiali presenti nella repository.

## 6. Pull Request e merge

Ogni Pull Request deve:

- Avere un titolo chiaro e descrittivo.
- Descrivere le modifiche introdotte e la loro motivazione.
- Fare riferimento all'issue associata, se presente.
- Essere sottoposta a *code review* secondo la [policy del repository](code-review-policy.md).
- Superare i controlli automatici richiesti.
- Non presentare conflitti irrisolti con il branch di destinazione.

La strategia di merge adottata è ***Squash and merge***: tutti i commit della Pull Request vengono riuniti in un unico commit sul branch `main`. Questa modalità è particolarmente adatta alla documentazione del progetto, poiché consente di mantenere una cronologia delle modifiche sintetica e leggibile, anche in presenza di numerosi commit intermedi, ad esempio durante la revisione dei documenti.

## 7. Eccezioni

Eventuali eccezioni al flusso standard devono essere motivate e concordate con il team.

Le eccezioni non devono compromettere la tracciabilità delle modifiche o la stabilità del branch principale.

## 8. Revisione del documento

Questa strategia può essere modificata tramite Pull Request quando emergono esigenze organizzative o tecniche che rendono necessario aggiornare il flusso di lavoro.