[翻訳元](https://microsoftlearning.github.io/mslearn-postgresql/Instructions/Labs/15-perform-extractive-and-abstractive-summarization.html)

# 抽出および抽象的な要約の実行

Margie's Travelが管理する賃貸物件アプリは、不動産管理者が賃貸物件を説明する方法を提供します。システムの説明の多くは長く、賃貸物件、その周辺、地元のアトラクション、店舗、その他の設備について多くの詳細が記載されています。アプリに新しい AI を活用した機能を実装する際に要望のあった機能は、ジェネレーティブ AI を使用してこれらの説明の簡潔な要約を作成し、ユーザーが物件をすばやく簡単に確認できるようにすることです。この演習では、Azure Database For PostgreSQL Flexible Server で `azure_ai` 拡張機能を使用して、賃貸物件の説明に対して抽象的および抽出的な要約を実行し、結果の概要を比較します。

## はじめに

管理者権限を持つ [Azure サブスクリプション](https://azure.microsoft.com/free)が必要であり、そのサブスクリプションで Azure OpenAI にアクセスすることが承認されている必要があります。Azure OpenAI へのアクセスが必要な場合は、[Azure OpenAI の制限付きアクセス](https://learn.microsoft.com/legal/cognitive-services/openai/limited-access)ページで申請してください。

### リソースを Azure サブスクリプションにデプロイする

この手順では、Azure Cloud Shell から Azure CLI コマンドを使用してリソース グループを作成し、Bicep スクリプトを実行して、この演習を完了するために必要な Azure サービスを Azure サブスクリプションにデプロイする方法について説明します。

> [!NOTE]
> このラーニングパスで複数のモジュールを実行している場合は、モジュール間で Azure 環境を共有できます。その場合は、このリソースのデプロイ手順を1回だけ完了する必要があります。

1. Web ブラウザーを開き、[Azure portal](https://portal.azure.com/) に移動します。

2. Azure portal ツールバーの \[**Cloud Shell**\] アイコンを選択して、ブラウザー ウィンドウの下部にある新しい [Cloud Shell](https://learn.microsoft.com/azure/cloud-shell/overview) ウィンドウを開きます。

![Cloud Shell Tool Bar](12-portal-toolbar-cloud-shell.png)

3. Cloud Shell プロンプトで、次のように入力して、演習用のリソースを含む GitHub リポジトリを複製します:

```bash
git clone https://github.com/MicrosoftLearning/mslearn-postgresql.git
```

4. 次に、3つのコマンドを実行して変数を定義し、Azure CLI コマンドを使用して Azure リソースを作成する際の冗長な入力を減らします。変数は、リソースグループに割り当てる名前 (`RG_NAME`)、リソースがデプロイされる Azure リージョン (`REGION`)、PostgreSQL 管理者ログイン用にランダムに生成されたパスワード (`ADMIN_PASSWORD`) を表します。

最初のコマンドでは、対応する変数に割り当てられた領域は `eastus` ですが、好みの場所に置き換えることもできます。ただし、既定値を置き換える場合は、[抽象的な概要作成をサポートする別の Azure リージョン](https://learn.microsoft.com/azure/ai-services/language-service/summarization/region-support)を選択して、このラーニングパスのモジュールのすべてのタスクを完了できるようにする必要があります。

```bash
REGION=eastus
```

次のコマンドは、この演習で使用するすべてのリソースを格納するリソースグループに使用する名前を割り当てます。対応する変数に割り当てられるリソースグループ名は `rg-learn-postgresql-ai-$REGION` で`REGION` は上記で指定した場所です。ただし、好みに合った他のリソースグループ名に変更できます。

```bash
RG_NAME=rg-learn-postgresql-ai-$REGION
```

最後のコマンドは、PostgreSQL 管理者ログインのパスワードをランダムに生成します。後で PostgreSQL Flexible Server に接続するときに使用するために、安全な場所にコピーします。

```bash
a=()
for i in {a..z} {A..Z} {0..9}; 
    do
    a[$RANDOM]=$i
done
ADMIN_PASSWORD=$(IFS=; echo "${a[*]::18}")
echo "Your randomly generated PostgreSQL admin user's password is:"
echo $ADMIN_PASSWORD
```

5. 複数の Azure サブスクリプションにアクセスでき、既定のサブスクリプションが、この演習のリソースグループやその他のリソースを作成するサブスクリプションではない場合は、次のコマンドを実行して適切なサブスクリプションを設定し、`<subscriptionName|subscriptionId>` トークンを使用するサブスクリプションの名前または ID に置き換えます:

```bash
az account set --subscription <subscriptionName|subscriptionId>
```

6. 次の Azure CLI コマンドを実行して、リソースグループを作成します:

```bash
az group create --name $RG_NAME --location $REGION
```

7. 最後に、Azure CLI を使用して Bicep デプロイスクリプトを実行し、リソースグループに Azure リソースをプロビジョニングします:

```bash
az deployment group create --resource-group $RG_NAME --template-file "mslearn-postgresql/Allfiles/Labs/Shared/deploy.bicep" --parameters restore=false adminLogin=pgAdmin adminLoginPassword=$ADMIN_PASSWORD
```

Bicep デプロイ スクリプトは、この演習を完了するために必要な Azure サービスをリソースグループにプロビジョニングします。デプロイされるリソースには、Azure Database for PostgreSQL Flexible Server、Azure OpenAI、Azure AI Language サービスが含まれます。また、Bicep スクリプトでは、PostgreSQL サーバーの許可リストへの `azure_ai` 拡張機能と `vector` 拡張機能の追加 (azure.extensions サーバーパラメーターを使用)、サーバー上に `rentals` という名前のデータベースを作成し、`text-embedding-ada-002` モデルを使用する `embedding` という名前のデプロイを Azure OpenAI サービスに追加するなど、いくつかの構成手順も実行されます。Bicep ファイルは、このラーニングパスのすべてのモジュールで共有されるため、一部の演習ではデプロイされたリソースの一部のみを使用できます。

通常、デプロイが完了するまでに数分かかります。Cloud Shell から監視するか、上記で作成したリソースグループの \[**デプロイ**\] ページに移動して、そこでデプロイの進行状況を確認できます。

Bicep デプロイスクリプトの実行時にいくつかのエラーが発生する場合があります。最も一般的なメッセージとその解決手順は次のとおりです:

* Azure AI Services リソースを以前に作成していない場合は、責任ある AI の利用条件が演習で用いるサブスクリプションで未読で同意されていないというメッセージが表示されることがあります:

```
{"code": "ResourceKindRequireAcceptTerms",
"message": "This subscription cannot create TextAnalytics until you agree to Responsible AI terms for this resource.
You can agree to Responsible AI terms by creating a resource through the Azure Portal and trying again."}
```

このエラーを解決するには、Azure portal から最初の言語リソースを作成し、使用条件を確認して承認できるようにする必要があります。ここで行うことができます: [https://portal.azure.com/#create/Microsoft.CognitiveServicesTextAnalytics](https://portal.azure.com/#create/Microsoft.CognitiveServicesTextAnalytics). ランダムで有効な名前を持つ新しいリソースグループの下に作成し、デプロイする Language サービスにランダムで有効な名前を割り当てます。その後、サブスクリプション全体の責任ある AI の条項に同意すると、同じ Azure サブスクリプションで任意のデプロイツール (SDK、CLI、ARM テンプレートなど) を使用して、後続の言語リソースを作成できます。そのため、ポータルで最初のリソースを作成したら、それを削除し、コマンドを再実行して Bicep デプロイスクリプトを実行できます。

* このラーニングパスの Bicep デプロイ スクリプトを以前に実行し、その後リソースを削除した場合、リソースを削除してから 48 時間以内にスクリプトを再実行しようとすると、次のようなエラー メッセージが表示されることがあります:

```
{"code": "InvalidTemplateDeployment",
"message": "The template deployment 'deploy' is not valid according to the validation procedure.
The tracking id is '4e87a33d-a0ac-4aec-88d8-177b04c1d752'. See inner errors for details."}

Inner Errors:
{"code": "FlagMustBeSetForRestore",
"message": "An existing resource with ID
'/subscriptions/{subscriptionId}/resourceGroups/rg-learn-postgresql-ai-eastus/providers/Microsoft.CognitiveServices/accounts/{accountName}'
has been soft-deleted.
To restore the resource, you must specify 'restore' to be 'true' in the property.
If you don't want to restore existing resource, please purge it first."}
```

このメッセージが表示された場合は、上記の `azure deployment group create` コマンドを変更して、`restore` パラメーターを `true` に設定して再実行します。

* 選択したリージョンで特定のリソースのプロビジョニングが制限されている場合は、`REGION` 変数を別の場所に設定し、Bicep デプロイ スクリプトを再実行する必要があります。

```
{"status":"Failed",
"error":{"code":"DeploymentFailed",
"target":"/subscriptions/{subscriptionId}/resourceGroups/{resourceGrouName}/providers/Microsoft.Resources/deployments/{deploymentName}",
"message":"At least one resource deployment operation failed.
Please list deployment operations for details.
Please see https://aka.ms/arm-deployment-operations for usage details.",
"details":[{"code":"ResourceDeploymentFailure",
"target":"/subscriptions/{subscriptionId}/resourceGroups/{resourceGrouName}/providers/Microsoft.DBforPostgreSQL/flexibleServers/{serverName}",
"message":"The resource write operation failed to complete successfully, because it reached terminal provisioning state 'Failed'.",
"details":[{"code":"RegionIsOfferRestricted",
"message":"Subscriptions are restricted from provisioning in this region.
Please choose a different region.
For exceptions to this rule please open a support request with Issue type of 'Service and subscription limits'.
See https://review.learn.microsoft.com/en-us/azure/postgresql/flexible-server/how-to-request-quota-increase for more details."}]}]}}
```

8. リソースのデプロイが完了したら、Cloud Shell ウィンドウを閉じます。

## Azure Cloud Shell で psql を使用してデータベースに接続する

このタスクでは、[Azure Cloud Shell](https://learn.microsoft.com/azure/cloud-shell/overview) から [psql コマンドラインユーティリティ](https://www.postgresql.org/docs/current/app-psql.html)を使用して、Azure Database for PostgreSQL Flexible Server 上の `rentals` データベースに接続します。

1. [Azure portal](https://portal.azure.com/) で、新しく作成した Azure Database for PostgreSQL Flexible Server に移動します。

2. リソースメニューの \[**設定**\] で \[**データベース**\] を選択し、`rentals` データベースの \[**接続**\] を選択します。
![Connect via psql](12-postgresql-rentals-database-connect.png)

3. Cloud Shell の \[Password for user pgAdmin\] プロンプトで、**pgAdmin** ログイン用にランダムに生成されたパスワードを入力します  。
ログインすると、`rentals` データベースの `psql` プロンプトが表示されます。

4. この演習の残りの部分では、Cloud Shell で作業を続けるため、ウィンドウの右上にある \[**最大化**\] ボタンを選択して、ブラウザー ウィンドウ内のウィンドウを展開すると便利な場合があります。

![Cloud Shell](12-azure-cloud-shell-pane-maximize.png)

## データベースにサンプルデータを取り込む

`azure_ai` 拡張機能を調べる前に、`rentals` データベースにいくつかのテーブルを追加し、サンプルデータを設定して、拡張機能の機能を確認するときに操作する情報を用意します。

1. 次のコマンドを実行して、賃貸物件のリストと顧客レビューのデータを格納するための `listings` と `reviews` のテーブルを作成します:

```sql
DROP TABLE IF EXISTS listings;
    
CREATE TABLE listings (
  id int,
  name varchar(100),
  description text,
  property_type varchar(25),
  room_type varchar(30),
  price numeric,
  weekly_price numeric
);
```

```sql
DROP TABLE IF EXISTS reviews;

CREATE TABLE reviews (
  id int,
  listing_id int, 
  date date,
  comments text
);
```

2. 次に、`COPY` コマンドを使用して、上記で作成した各テーブルに CSV ファイルからデータをロードします。まず、次のコマンドを実行して `listings` テーブルにデータを入力します:

```sql
\COPY listings FROM 'mslearn-postgresql/Allfiles/Labs/Shared/listings.csv' CSV HEADER
```

コマンド出力は `COPY 50` で、CSV ファイルからテーブルに 50 行が書き込まれたことを示します。

3. 最後に、以下のコマンドを実行して、カスタマーレビューを `reviews` テーブルにロードします:

```sql
\COPY reviews FROM 'mslearn-postgresql/Allfiles/Labs/Shared/reviews.csv' CSV HEADER
```

コマンド出力は `COPY 354` で、CSV ファイルからテーブルに 354 行が書き込まれたことを示します。

## azure_ai 拡張機能のインストールと構成 

`azure_ai` 拡張機能を使用する前に、拡張機能をデータベースにインストールし、Azure AI Services リソースに接続するように構成する必要があります。`azure_ai` 拡張機能を使用すると、Azure OpenAI と Azure AI Language サービスをデータベースに統合できます。データベースで拡張機能を有効にするには、次の手順を実行します:

1. `psql` プロンプトで次のコマンドを実行して、環境の設定時に実行した Bicep デプロイスクリプトによって、`azure_ai` 拡張機能と `vector` 拡張機能がサーバーの許可リストに正常に追加されたことを確認します:

```sql
SHOW azure.extensions;
```

このコマンドは、サーバーの許可リストにある拡張機能のリストを表示します。すべてが正しくインストールされた場合、出力には次のように `azure_ai` と `vector` が含まれている必要があります:

```sql
  azure.extensions 
 ------------------
  azure_ai,vector
```

拡張機能を Azure Database for PostgreSQL Flexible Serverデータベースにインストールして使用する前に、「[PostgreSQL 拡張機能の使用方法](https://learn.microsoft.com/azure/postgresql/flexible-server/concepts-extensions#how-to-use-postgresql-extensions)」の説明に従って、サーバーの許可リストに追加する必要があります。

2. これで、[CREATE EXTENSION](https://www.postgresql.org/docs/current/sql-createextension.html) コマンドを使用して `azure_ai` 拡張機能をインストールする準備が整いました。

```sql
CREATE EXTENSION IF NOT EXISTS azure_ai;
```

`CREATE EXTENSION` は、スクリプトファイルを実行して、新しい拡張機能をデータベースにロードします。このスクリプトは、通常、関数、データ型、スキーマなどの新しい SQL オブジェクトを作成します。同じ名前の拡張機能が既に存在する場合は、エラーがスローされます。`IF NOT EXISTS` を追加すると、コマンドが既にインストールされている場合にエラーをスローせずに実行できます。

## Azure AI Services アカウントと接続する

`azure_ai` 拡張機能の `azure_cognitive` スキーマに含まれる Azure AI サービス統合は、データベースから直接アクセスできる豊富な AI 言語機能のセットを提供します。テキスト要約機能は、[Azure AI Language サービス](https://learn.microsoft.com/azure/ai-services/language-service/overview)を通じて有効になります。

1. `azure_openai` 関数と同様に、`azure_ai` 拡張機能を使用して Azure AI Services に対して呼び出しを正常に行うには、Azure AI Language サービスのエンドポイントとキーを指定する必要があります。Cloud Shell が開いているのと同じブラウザー タブを使用して、Cloud Shell ウィンドウを最小化または復元し、[Azure portal](https://portal.azure.com/) で Language サービスリソースに移動します。リソース メニューの\[**リソース管理**\]セクションで、\[**キーとエンドポイント**\]を選択します。

![Key for cognitive](12-azure-language-service-keys-and-endpoints.png)

> [!NOTE]
> 先に `azure_ai` 拡張機能をインストールし、Language サービスのエンドポイントとキーを事前に設定した際に、`NOTICE: extension "azure_ai" already exists, skipping CREATE EXTENSION` というメッセージが表示された場合は、`azure_ai.get_setting()` 関数を使用して、これらの設定が正しいことを確認し、正しい場合は手順 2 をスキップできます。

2. エンドポイントとアクセスキーの値をコピーし、次のコマンドで、`{endpoint}` トークンと `{api-key}` トークンを Azure portal からコピーした値に置き換えます。Cloud Shell の `psql` コマンドプロンプトからコマンドを実行して、値を `azure_ai.settings` テーブルに追加します。

```sql
SELECT azure_ai.set_setting('azure_cognitive.endpoint', '{endpoint}');
```

```sql
SELECT azure_ai.set_setting('azure_cognitive.subscription_key', '{api-key}');
```

## 拡張機能の概要機能を確認する

このタスクでは、`azure_cognitive` スキーマの 2 つの要約機能を確認します。

1. この演習の残りの部分では、Cloud Shell で作業を続けるため、ウィンドウの右上にある \[**最大化**\] ボタンを選択して、ブラウザー ウィンドウ内のウィンドウを展開すると便利な場合があります。

![Cloud Shell](12-azure-cloud-shell-pane-maximize.png)

2. Cloud Shell で `psql` を操作する場合、クエリ結果の拡張表示を有効にすると、後続のコマンドの出力の読みやすさが向上するため、役立つ場合があります。次のコマンドを実行して、拡張表示を自動的に適用できるようにします。

```sql
\x auto
```

3. `azure_ai` 拡張機能のテキスト要約関数は、`azure_cognitive` スキーマ内にあります。抽出要約の場合は、`summarize_extractive()` 関数を使用します。[`\df` メタコマンド](https://www.postgresql.org/docs/current/app-psql.html#APP-PSQL-META-COMMAND-DF-LC)を使用して、関数を調べるには、次のコマンドを実行します:

```sql
\df azure_cognitive.summarize_extractive
```

メタコマンドの出力には、関数のスキーマ、名前、結果のデータ型、および引数が表示されます。この情報は、クエリから関数を操作する方法を理解するのに役立ちます。

出力には `summarize_extractive()` 関数の 3 つのオーバーロードが表示され、それらの違いを確認できます。出力の `Argument データ型`プロパティは、3 つの関数オーバーロードが想定する引数の一覧を示します:

| 引数 | データ型 | デフォルト値 | 説明 |
| --- | --- | --- | --- |
|text | `text` または `text\[\]` |  | 要約を生成するテキスト (またはテキストの配列)。 |
|language_text | `text` または `text\[\]` |  | 要約するテキストの言語を表す言語コード (または言語コードの配列)。[サポートされている言語の一覧](https://learn.microsoft.com/azure/ai-services/language-service/summarization/language-support)を確認して、必要な言語コードを取得します。 |
|sentence_count | `integer` | 3 | 生成する要約文の数 |
|sort_by | `text` | 'offset' | 生成される要約文のソート順。指定できる値は「offset」と「rank」で、offset は元のコンテンツ内の抽出された各文の開始位置を表し、rank は文がコンテンツのメインアイデアにどの程度関連しているかを示す AI 生成の指標です。 |
|batch_size | `integer` | 25 | `text[]` の入力を期待する 2 つのオーバーロードの場合のみ。一度に処理するレコードの数を指定します。 |
|disable_service_logs | `boolean` | false | サービスログをオフにするかどうかを示すフラグ。 |
|timeout_ms | `integer` | 3600000 | 操作が停止するまでのタイムアウト (ミリ秒単位)。|
|throw_on_error | `boolean` | true | 関数がエラー時に例外をスローして、ラップしているトランザクションをロールバックするかどうかを示すフラグ。|
|max_attempts | `integer` | 1 | 障害発生時に Azure OpenAI サービスの呼び出しを再試行する回数。|
|retry_delay_ms | `integer` | 1000 | Azure OpenAI サービス エンドポイントの呼び出しを再試行するまでに待機する時間 (ミリ秒単位)。|

4. 上記の手順を繰り返しますが、今回は `azure_cognitive.summarize_abstractive()` 関数に対して [`\df` メタコマンド](https://www.postgresql.org/docs/current/app-psql.html#APP-PSQL-META-COMMAND-DF-LC)を実行し、出力を確認します。

2 つの関数のシグネチャは似ていますが、`summarize_abstractive()` には `sort_by` パラメーターがなく、`summarize_extractive()` 関数によって返される `azure_cognitive.sentence` 複合型の配列に対して `text` の配列が返されます。この不一致は、2つの異なる方法が要約を生成する方法に関係しています。抽出要約は、要約するテキスト内の最も重要な文を識別し、それらをランク付けし、それらを要約として返します。一方、抽象要約は、生成AIを使用して、テキストの要点を要約した新しいオリジナルの文章を作成します。

5. また、クエリで出力を正しく処理できるように、関数が返すデータ型の構造を理解することも不可欠です。`summarize_extractive()` 関数によって返される `azure_cognitive.sentence` 型を調べるには:

```sql
\dT+ azure_cognitive.sentence
```

このコマンドの出力は、次のようになります:

```sql
                         Composite type "azure_cognitive.sentence"
     Column  |     Type         | Collation | Nullable | Default | Storage  | Description 
 ------------+------------------+-----------+----------+---------+----------+-------------
  text       | text             |           |           |        | extended | 
  rank_score | double precision |           |           |        | plain    |
```

`azure_cognitive.sentence` は、抽出文のテキストと各文のランクスコアを含む複合型であり、文がテキストのメイントピックにどの程度関連しているかを示します。ドキュメントの概要では、抽出された文がランク付けされ、表示される順序で返されるか、ランクに従って返されるかを決定できます。

## 物件の説明の要約を作成する

このタスクでは、`summarize_extractive()` 関数と `summarize_abstractive()` 関数を使用して、物件の説明に簡潔な 2 つの要約文を作成します。

1. `summarize_extractive()` 関数とそれが返す `sentiment_analysis_result` を確認したので、関数を使用してみましょう。次の単純なクエリを実行して、`reviews` テーブル内の少数のコメントに対して感情分析を実行します:

```sql
SELECT
  id,
  name,
  description,
  azure_cognitive.summarize_extractive(description, 'en', 2) AS extractive_summary
FROM listings
WHERE id IN (1, 2);
```

出力の `extractive_summary` フィールドの 2 つの文を元の説明と比較し、文がオリジナルではなく、説明から抽出されたことを確認します。各文の後に表示される数値は、Language サービスによって割り当てられたランク スコアです。

2. 次に、同一のレコードに対して抽象的な要約を実行します:

```sql
SELECT
  id,
  name,
  description,
  azure_cognitive.summarize_abstractive(description, 'en', 2) AS abstractive_summary
FROM listings
WHERE id IN (1, 2);
```

拡張機能の抽象的な要約機能は、元のテキストの全体的な意図をカプセル化する一意の自然言語の要約を提供します。

次のようなエラーが表示された場合は、Azure 環境の作成時に抽象的な要約をサポートしていないリージョンを選択しました:

```bash
ERROR: azure_cognitive.summarize_abstractive: InvalidRequest: Invalid Request.

InvalidParameterValue: Job task: 'AbstractiveSummarization-task' failed with validation errors: ['Invalid Request.']

InvalidRequest: Job task: 'AbstractiveSummarization-task' failed with validation error: Document abstractive summarization is not supported in the region Central US. The supported regions are North Europe, East US, West US, UK South, Southeast Asia.
```

この手順を実行し、抽象的な要約を使用して残りのタスクを完了できるようにするには、エラーメッセージで指定されたサポートされているリージョンのいずれかに新しい Azure AI Language サービスを作成する必要があります。このサービスは、他のラボリソースに使用したのと同じリソースグループにプロビジョニングできます。または、残りのタスクを抽出要約に置き換えることもできますが、2 つの異なる要約手法の出力を比較できるという利点はありません。

3. 最後のクエリを実行して、2 つの要約手法を並べて比較します:

```sql
SELECT
  id,
  azure_cognitive.summarize_extractive(description, 'en', 2) AS extractive_summary,
  azure_cognitive.summarize_abstractive(description, 'en', 2) AS abstractive_summary
FROM listings
WHERE id IN (1, 2);
```

生成された要約を並べて配置することで、各方法で生成された要約の品質を簡単に比較できます。Margie's Travel アプリケーションの場合、抽象的な要約の方が適しており、自然で読みやすい方法で高品質の情報を提供する簡潔な要約を提供します。いくつかの詳細を提供しますが、抽出要約はよりばらばらであり、抽象的な要約によって作成された元のコンテンツよりも価値が低くなります。

## データベースに説明の要約を保存する

1. 次のクエリを実行して、`listings` テーブルを変更し、新しい `summary` 列を追加します:

```sql
ALTER TABLE listings
ADD COLUMN summary text;
```

2. ジェネレーティブ AI を使用してデータベース内の既存のすべての物件の概要を作成するには、説明をバッチで送信して、Language サービスが複数のレコードを同時に処理できるようにするのが最も効率的です。

```sql
WITH batch_cte AS (
  SELECT azure_cognitive.summarize_abstractive(ARRAY(SELECT description FROM listings ORDER BY id), 'en', batch_size => 25) AS summary
),
summary_cte AS (
  SELECT
    ROW_NUMBER() OVER () AS id,
    ARRAY_TO_STRING(summary, ',') AS summary
    FROM batch_cte
)
UPDATE listings AS l
SET summary = s.summary
FROM summary_cte AS s
WHERE l.id = s.id;
```

`UPDATE` ステートメントは、2 つの共通テーブル式 (CTE) を使用してデータを操作してから、`listings` テーブルを要約で更新します。最初の CTE (`batch_cte`) は、`listings` テーブルからすべての `description` 値を Language サービスに送信して、抽象的な概要を生成します。これは、一度に 25 レコードのバッチで行われます。2 番目の CTE (`summary_cte`) は、`summarize_abstractive()` 関数によって返された要約の順位を使用して、各要約に、`listings` テーブル内の `description` の元のレコードに対応する `id` を割り当てます。また、`ARRAY_TO_STRING` 関数を使用して、生成された要約をテキスト配列(`text[]`)の戻り値から引き出し、単純な文字列に変換します。最後に、`UPDATE` ステートメントは、関連するリストの `listings` テーブルに要約を書き込みます。

3. 最後の手順として、クエリを実行して、`listings` テーブルに書き込まれた概要を表示します:

```sql
SELECT
  id,
  name,
  description,
  summary
FROM listings
LIMIT 5;
```

## リストのレビューの AI サマリーを生成する

Margie's Travel アプリの場合、宿泊施設のすべてのクチコミの概要を表示すると、ユーザーはクチコミの全体的な要点をすばやく把握できます。

1. 次のクエリを実行して、リストのすべてのレビューを 1 つの文字列に結合し、その文字列に対して抽象的な要約を生成します:

```sql
SELECT unnest(azure_cognitive.summarize_abstractive(reviews_combined, 'en')) AS review_summary
FROM (
  -- Combine all reviews for a listing
  SELECT string_agg(comments, ' ') AS reviews_combined
  FROM reviews
  WHERE listing_id = 1
);
```

## クリーンアップ

この演習を完了したら、作成した Azure リソースを削除します。データベースの使用量ではなく、構成された容量に対して課金されます。次の手順に従って、リソース グループと、このラボ用に作成したすべてのリソースを削除します。
> [!NOTE]
> このラーニング パスで追加のモジュールを完了する予定がある場合は、完了する予定のすべてのモジュールを完了するまで、このタスクをスキップできます。

1. Web ブラウザーを開いて [Azure portal](https://portal.azure.com/) に移動し、ホームページで Azure サービスの\[**リソースグループ**\]を選択します。

![Select RG](12-azure-portal-home-azure-services-resource-groups.png)

2. 任意のフィールドの検索ボックスに、このラボ用に作成したリソースグループの名前を入力し、一覧からリソースグループを選択します。

3. リソースグループの\[**概要**\]ページで、\[**リソース グループの削除**\]を選択します。

![Delete RG](12-resource-group-delete.png)

4. 確認ダイアログで、削除するリソース グループ名を入力して確認し、\[**削除**\]を選択します。
