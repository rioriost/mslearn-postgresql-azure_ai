Azure Database for PostgreSQL Flexible Serverでazure_aiエクステンションを用いるハンズオンの日本語訳です。

[翻訳元](https://microsoftlearning.github.io/mslearn-postgresql/Instructions/Labs/12-explore-azure-ai-extension.html)

# Azure AI 拡張機能を調べる

Margie's Travel の主任開発者であるあなたは、賃貸物件に関するインテリジェントなレコメンデーションを顧客に提供する AI を活用したアプリケーションを構築する任務を負っています。Azure Database for PostgreSQL の `azure_ai` 拡張機能の詳細と、ジェネレーティブ AI (GenAI) の機能をアプリに統合するのにどのように役立つかについて学習する必要があります。この演習では、`azure_ai` 拡張機能を Azure Database for PostgreSQL Flexible Server にインストールし、Azure AI サービスと ML サービスを統合するための機能を調べることで、拡張機能とその機能を調べます。

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

Bicep デプロイ スクリプトは、この演習を完了するために必要な Azure サービスをリソースグループにプロビジョニングします。デプロイされるリソースには、Azure Database for PostgreSQL Flexible Server、Azure OpenAI、Azure AI 言語サービスが含まれます。また、Bicep スクリプトでは、PostgreSQL サーバーの許可リストへの `azure_ai` 拡張機能と `vector` 拡張機能の追加 (azure.extensions サーバーパラメーターを使用)、サーバー上に `rentals` という名前のデータベースを作成し、`text-embedding-ada-002` モデルを使用する `embedding` という名前のデプロイを Azure OpenAI サービスに追加するなど、いくつかの構成手順も実行されます。Bicep ファイルは、このラーニングパスのすべてのモジュールで共有されるため、一部の演習ではデプロイされたリソースの一部のみを使用できます。

通常、デプロイが完了するまでに数分かかります。Cloud Shell から監視するか、上記で作成したリソースグループの \[**デプロイ**\] ページに移動して、そこでデプロイの進行状況を確認できます。

Bicep デプロイスクリプトの実行時にいくつかのエラーが発生する場合があります。最も一般的なメッセージとその解決手順は次のとおりです:

* Azure AI Services リソースを以前に作成していない場合は、責任ある AI の利用条件が演習で用いるサブスクリプションで未読で同意されていないというメッセージが表示されることがあります:

```
{"code": "ResourceKindRequireAcceptTerms",
"message": "This subscription cannot create TextAnalytics until you agree to Responsible AI terms for this resource.
You can agree to Responsible AI terms by creating a resource through the Azure Portal and trying again."}
```

このエラーを解決するには、Azure portal から最初の言語リソースを作成し、使用条件を確認して承認できるようにする必要があります。ここで行うことができます: [https://portal.azure.com/#create/Microsoft.CognitiveServicesTextAnalytics](https://portal.azure.com/#create/Microsoft.CognitiveServicesTextAnalytics). ランダムで有効な名前を持つ新しいリソースグループの下に作成し、デプロイする言語サービスにランダムで有効な名前を割り当てます。その後、サブスクリプション全体の責任ある AI の条項に同意すると、同じ Azure サブスクリプションで任意のデプロイツール (SDK、CLI、ARM テンプレートなど) を使用して、後続の言語リソースを作成できます。そのため、ポータルで最初のリソースを作成したら、それを削除し、コマンドを再実行して Bicep デプロイスクリプトを実行できます。

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

[Cloud Shell](12-azure-cloud-shell-pane-maximize.png)

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

`azure_ai` 拡張機能を使用する前に、拡張機能をデータベースにインストールし、Azure AI Services リソースに接続するように構成する必要があります。`azure_ai` 拡張機能を使用すると、Azure OpenAI と Azure AI 言語サービスをデータベースに統合できます。データベースで拡張機能を有効にするには、次の手順を実行します:

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

## azure_ai拡張機能に含まれるオブジェクトを確認する 

`azure_ai` 拡張機能内のオブジェクトを確認すると、その機能をよりよく理解するのに役立ちます。このタスクでは、拡張機能によってデータベースに追加されたさまざまなスキーマ、ユーザー定義関数 (UDF)、および複合型を検査します。

1. Cloud Shell で `psql` を操作する場合、クエリ結果の拡張表示を有効にすると、後続のコマンドの出力の読みやすさが向上するため、役立つ場合があります。次のコマンドを実行して、拡張表示を自動的に適用できるようにします。

```sql
\x auto
```

3. [`\dx` メタコマンド](https://www.postgresql.org/docs/current/app-psql.html#APP-PSQL-META-COMMAND-DX-LC)は、拡張機能内に含まれるオブジェクトを一覧表示するために使用されます。`psql` コマンドプロンプトから次のコマンドを実行して、`azure_ai` 拡張機能のオブジェクトを表示します。スペースバーを押すと、オブジェクトの完全なリストが表示される場合があります。

```sql
\dx+ azure_ai
```

メタコマンドの出力は、`azure_ai` 拡張機能が4つのスキーマ、複数のユーザー定義関数 (UDF)、データベース内の複数の複合型、および `azure_ai.settings` テーブルを作成することを示しています。スキーマ以外のすべてのオブジェクト名の前には、そのオブジェクトが属するスキーマが付きます。スキーマは、拡張機能がバケットに追加する関連する関数と型をグループ化するために使用されます。次の表に、拡張機能によって追加されるスキーマと、それぞれの簡単な説明を示します:

| スキーマ | 説明 |
| --- | --- |
|azure_ai | 拡張機能と対話するための構成テーブルと UDF が存在するプリンシパル スキーマ。|
|azure_openai | Azure OpenAI エンドポイントの呼び出しを可能にする UDF が含まれています。|
|azure_cognitive | データベースと Azure AI Services の統合に関連する UDF と複合型を提供します。|
|azure_ml | Azure Machine Learning (ML) サービスを統合するための UDF が含まれています。|

### Azure AI スキーマを調べる

`azure_ai` スキーマは、データベースから Azure AI および ML サービスと直接対話するためのフレームワークを提供します。これには、これらのサービスへの接続を設定し、同じスキーマでホストされている `settings` テーブルからそれらを取得するための関数が含まれています。`settings` テーブルは、Azure AI および ML サービスに関連付けられているエンドポイントとキーのデータベース内の安全なストレージを提供します。

1. スキーマで定義されている関数を確認するには、[`\df` メタコマンド](https://www.postgresql.org/docs/current/app-psql.html#APP-PSQL-META-COMMAND-DF-LC)を使用して、関数を表示するスキーマを指定します。次のコマンドを実行して、`azure_ai` スキーマの関数を表示します:

```sql
\df azure_ai.*
```

コマンドの出力は、次のようなテーブルになります:

```sql
               List of functions
  Schema |  Name  | Result data type | Argument data types | Type 
 ----------+-------------+------------------+----------------------+------
  azure_ai | get_setting | text      | key text      | func
  azure_ai | set_setting | void      | key text, value text | func
  azure_ai | version  | text      |           | func
```

`set_setting()` 関数を使用すると、Azure AI サービスと ML サービスのエンドポイントとキーを設定して、拡張機能がそれらに接続できるようにすることができます。**キー**とそれに割り当てる**値**を受け入れます。`azure_ai.get_setting()` 関数は、`set_setting()` 関数で設定した値を取得する方法を提供します。表示する設定の**キー**を受け取り、割り当てられた値を返します。どちらの方法でも、キーは次のいずれかである必要があります:

| Key | Description |
| --- | ----------- |
| azure_openai.endpoint | サポートされている OpenAI エンドポイント (e.g., https://example.openai.azure.com)|
| azure_openai.subscription_key | Azure OpenAI リソースのサブスクリプション キー。|
| azure_cognitive.endpoint | サポートされている Azure AI Services エンドポイント (e.g., https://example.cognitiveservices.azure.com).|
| azure_cognitive.subscription_key | Azure AI Services リソースのサブスクリプション キー。|
| azure_ml.scoring_endpoint | サポートされている Azure ML スコアリング エンドポイント (e.g., https://example.eastus2.inference.ml.azure.com/score)|
| azure_ml.endpoint_key | Azure ML デプロイのエンドポイント キー。|

> [!IMPORTANT]
> API キーを含む Azure AI サービスの接続情報はデータベースの構成テーブルに格納されるため、`azure_ai` 拡張機能では、`azure_ai_settings_manager` と呼ばれるロールを定義して、この情報が保護され、そのロールが割り当てられているユーザーのみがアクセスできるようにします。このロールは、拡張機能に関連する設定の読み取りと書き込みを可能にします。`azure_ai_settings_manager` ロールのメンバーのみが、`azure_ai.get_setting()` 関数と `azure_ai.set_setting()` 関数を呼び出すことができます。Azure Database for PostgreSQL Flexible Serverでは、すべての管理者ユーザー (`azure_pg_admin` ロールが割り当てられているユーザー) にも `azure_ai_settings_manager` ロールが割り当てられます。

2. `azure_ai.set_setting()` 関数と `azure_ai.get_setting()` 関数の使用方法を示すために、Azure OpenAI アカウントへの接続を構成します。Cloud Shell が開いているのと同じブラウザー タブを使用して、Cloud Shell ウィンドウを最小化または復元し、Azure portal で Azure OpenAI リソースに移動します。Azure OpenAI リソースページに移動したら、リソース メニューの\[**リソース管理**\]セクションで\[**キーとエンドポイント**\]を選択し、エンドポイントと使用可能なキーの1つをコピーします。

![Select Key](12-azure-openai-keys-and-endpoints.png)

`KEY 1` または `KEY 2` のいずれかを使用できます。常に2つのキーを持つことで、サービスを中断することなく、キーを安全にローテーションおよび再生成できます。

3. エンドポイントとキーを取得したら、Cloud Shell ペインを再度最大化し、次のコマンドを使用して構成テーブルに値を追加します。`{endpoint}` トークンと `{api-key}` トークンは、必ず Azure portal からコピーした値に置き換えてください。

```sql
SELECT azure_ai.set_setting('azure_openai.endpoint', '{endpoint}');
```

```sql
SELECT azure_ai.set_setting('azure_openai.subscription_key', '{api-key}');
```

5. `azure_ai.settings` テーブルに書き込まれた設定は、次のクエリで `azure_ai.get_setting()` 関数を使用して確認できます:

```sql
SELECT azure_ai.get_setting('azure_openai.endpoint');
SELECT azure_ai.get_setting('azure_openai.subscription_key');
```

これで、`azure_ai` 拡張機能が Azure OpenAI アカウントに接続されました。

### Azure OpenAI スキーマを確認する

`azure_openai` スキーマは、Azure OpenAI を使用して、テキスト値のベクトル埋め込みの作成をデータベースに統合する機能を提供します。このスキーマを使用すると、データベースから直接 (Azure OpenAI で埋め込みを生成)[https://learn.microsoft.com/azure/ai-services/openai/how-to/embeddings]して、入力テキストのベクター表現を作成し、ベクター類似性検索で使用したり、機械学習モデルで使用したりできます。スキーマには、2つのオーバーロードを持つ1つの関数 `create_embeddings()` が含まれています。1つのオーバーロードは1つの入力文字列を受け取り、もう1つのオーバーロードは入力文字列の配列を想定しています。

1. 上記で行ったように、[`\df` メタコマンド](https://www.postgresql.org/docs/current/app-psql.html#APP-PSQL-META-COMMAND-DF-LC)を使用して、`azure_openai` スキーマ内の関数の詳細を表示できます:

```sql
\df azure_openai.*
```

出力には、`azure_openai.create_embeddings` 関数の2つのオーバーロードが表示され、関数の2つのバージョンとそれらが返す型の違いを確認できます。出力の `Argument データ型`プロパティは、2つの関数オーバーロードで想定される引数の一覧を示します:

| 引数 | データ型 | デフォルト値 | 説明 |
| --- | --- | --- | --- |
|deployment_name | `text` |  | `text-embedding-ada-002` モデルを含む Azure OpenAI Studio のデプロイの名前 |
|input | `text` または `text\[\]` |  | 埋め込みが作成される入力テキスト (またはテキストの配列)。 |
|batch_size | `integer` | 100 | `text\[\]`の入力を想定するオーバーロードの場合のみ。一度に処理するレコードの数を指定します。 |
|timeout_ms | `integer` | 3600000 | 操作が停止するまでのタイムアウト (ミリ秒単位)。|
|throw_on_error | `boolean` | true | 関数がエラー時に例外をスローして、ラップしているトランザクションをロールバックするかどうかを示すフラグ。|
|max_attempts | `integer` | 1 | 障害発生時に Azure OpenAI サービスの呼び出しを再試行する回数。|
|retry_delay_ms | `integer` | 1000 | Azure OpenAI サービス エンドポイントの呼び出しを再試行するまでに待機する時間 (ミリ秒単位)。|

2. この関数の簡単な使用例を示すには、次のクエリを実行して、`listings` テーブルの `description` フィールドのベクトル埋め込みを作成します。 関数の `deployment name` パラメーターは、Azure OpenAI サービスでの `text-embedding-ada-002` モデルのデプロイの名前である `embedding` に設定されます (Bicep デプロイスクリプトによってその名前で作成されました):

```sql
SELECT
  id,
  name,
  azure_openai.create_embeddings('embedding', description) AS vector
FROM listings
LIMIT 1;
```

出力は次のようになります:

```sql
  id |      name       |              vector
 ----+-------------------------------+------------------------------------------------------------
   1 | Stylish One-Bedroom Apartment | {0.020068742,0.00022734122,0.0018286322,-0.0064167166,...}
```

簡潔にするために、上記の出力ではベクトル埋め込みを省略しています。

(埋め込み)[https://learn.microsoft.com/azure/postgresql/flexible-server/generative-ai-overview#embeddings]は、機械学習と自然言語処理 (NLP) の概念であり、単語、ドキュメント、エンティティなどのオブジェクトを多次元空間の(ベクトル)[https://learn.microsoft.com/azure/postgresql/flexible-server/generative-ai-overview#vectors]として表現します。埋め込みにより、機械学習モデルで2つの情報がどの程度密接に関連しているかを評価できます。この手法は、データ間の関係と類似性を効率的に識別し、アルゴリズムがパターンを識別し、正確な予測を行うことを可能にします。

`azure_ai` 拡張機能を使用すると、入力テキストの埋め込みを生成できます。生成されたベクトルを残りのデータと一緒にデータベースに格納できるようにするには、データベース資料の「(ベクター・サポートの使用可能化)[https://learn.microsoft.com/azure/postgresql/flexible-server/how-to-use-pgvector#enable-extension]」のガイダンスに従って、`vector` 拡張をインストールする必要があります。ただし、これはこの演習の範囲外です。

### azure_cognitive スキーマを調べる

`azure_cognitive` スキーマは、データベースから Azure AI Services と直接対話するためのフレームワークを提供します。スキーマ内の Azure AI サービス統合では、データベースから直接アクセスできる豊富な AI 言語機能セットが提供されます。機能には、感情分析、言語検出、キーフレーズ抽出、エンティティ認識、テキスト要約、翻訳が含まれます。これらの機能は、(Azure AI 言語サービス)[https://learn.microsoft.com/azure/ai-services/language-service/overview]を通じて有効になります。

1. スキーマで定義されているすべての関数を確認するには、以前と同様に[`\df` メタコマンド](https://www.postgresql.org/docs/current/app-psql.html#APP-PSQL-META-COMMAND-DF-LC)を使用できます。`azure_cognitive` スキーマの関数を表示するには、次のコマンドを実行します:

```sql
\df azure_cognitive.*
```

2. このスキーマには多数の関数が定義されているため、[`\df` メタコマンド](https://www.postgresql.org/docs/current/app-psql.html#APP-PSQL-META-COMMAND-DF-LC)からの出力は読みにくい場合があるため、小さなチャンクに分割するのが最善です。次のコマンドを実行して、`analyze_sentiment()` 関数だけを確認します:

```sql
\df azure_cognitive.analyze_sentiment
```

出力では、関数に3つのオーバーロードがあり、1つは1つの入力文字列を受け入れ、他の2つはテキストの配列を期待しています。出力には、関数のスキーマ、名前、結果のデータ・タイプ、および引数の・データ・タイプが表示されます。この情報は、関数の使用方法を理解するのに役立ちます。

3. 上記のコマンドを繰り返して、`analyze_sentiment` 関数名を次の各関数名に置き換えて、スキーマで使用可能なすべての関数を検査します:

* `detect_language`
* `extract_key_phrases`
* `linked_entities`
* `recognize_entities`
* `recognize_pii_entities`
* `summarize_abstractive`
* `summarize_extractive`
* `translate`

関数ごとに、関数のさまざまな形式と、予想される入力と結果のデータ型を調べます。

4. 関数の他に、`azure_cognitive` スキーマには、さまざまな関数からの戻り値のデータ型として使用されるいくつかの複合型も含まれています。クエリで出力を正しく処理できるように、関数が返すデータ型の構造を理解することが不可欠です。たとえば、次のコマンドを実行して、`sentiment_analysis_result` の種類を検査します:

```sql
\dT+ azure_cognitive.sentiment_analysis_result
```

5. 上記のコマンドの出力は、`sentiment_analysis_result` 型が`タプル`であることを示しています。次のコマンドを実行して、`sentiment_analysis_result` 型に含まれる列を調べることで、その`タプル`の構造をさらに掘り下げることができます:

```sql
\d+ azure_cognitive.sentiment_analysis_result
```

このコマンドの出力は、次のようになります:

```sql
          Composite type "azure_cognitive.sentiment_analysis_result"
    Column  |   Type   | Collation | Nullable | Default | Storage | Description 
 ----------------+------------------+-----------+----------+---------+----------+-------------
  sentiment   | text      |     |     |    | extended | 
  positive_score | double precision |     |     |    | plain  | 
  neutral_score | double precision |     |     |    | plain  | 
  negative_score | double precision |     |     |    | plain  |
```

`azure_cognitive.sentiment_analysis_result` は、入力テキストのセンチメント予測を含む複合型です。これには、肯定的、否定的、中立的、または混合の感情と、テキストで見つかった肯定的、中立的、否定的な側面のスコアが含まれます。スコアは0から1までの実数で表されます。たとえば、(neutral, 0.26, 0.64, 0.09) では、センチメントは中立で、正のスコアは 0.26、中立は 0.64、負のスコアは 0.09 です。

6. `azure_openai` 関数と同様に、`azure_ai` 拡張機能を使用して Azure AI Services に対して呼び出しを正常に行うには、Azure AI 言語サービスのエンドポイントとキーを指定する必要があります。Cloud Shell が開いているのと同じブラウザー タブを使用して、Cloud Shell ウィンドウを最小化または復元し、(Azure portal)[https://portal.azure.com/] で言語サービスリソースに移動します。リソース メニューの\[**リソース管理**\]セクションで、\[**キーとエンドポイント**\]を選択します。

[Key for cognitive](12-azure-language-service-keys-and-endpoints.png)

7. エンドポイントとアクセス キーの値をコピーし、`{endpoint}` トークンと `{api-key}` トークンを Azure portal からコピーした値に置き換えます。Cloud Shell を再度最大化し、Cloud Shell の `psql` コマンド プロンプトからコマンドを実行して、構成テーブルに値を追加します。

```sql
SELECT azure_ai.set_setting('azure_cognitive.endpoint', '{endpoint}');
```

```sql
SELECT azure_ai.set_setting('azure_cognitive.subscription_key', '{api-key}');
```

8. 次に、次のクエリを実行して、いくつかのレビューのセンチメントを分析します:

```sql
SELECT
  id,
  comments,
  azure_cognitive.analyze_sentiment(comments, 'en') AS sentiment
FROM reviews
WHERE id IN (1, 3);
```

出力の`センチメント`値、`(mixed,0.71,0.09,0.2)` と `(positive,0.99,0.01,0.2)` を観察します。これらは、上記のクエリの `analyze_sentiment()` 関数によって返される`sentiment_analysis_result` を表します。分析は、`reviews` テーブルの `comments` フィールドに対して実行されました。

## Azure ML スキーマを検査する

`azure_ml` スキーマを使用すると、関数はデータベースから直接 Azure ML サービスに接続できます。

1. スキーマで定義されている関数を確認するには、[`\df` メタコマンド](https://www.postgresql.org/docs/current/app-psql.html#APP-PSQL-META-COMMAND-DF-LC)を使用できます。`azure_ml` スキーマの関数を表示するには:

```sql
\df azure_ml.*
```

出力では、このスキーマに `azure_ml.inference()` と `azure_ml.invoke()` の2つの関数が定義されており、その詳細を以下に示します:

```sql
               List of functions
 -----------------------------------------------------------------------------------------------------------
 Schema       | azure_ml
 Name        | inference
 Result data type  | jsonb
 Argument data types | input_data jsonb, deployment_name text DEFAULT NULL::text, timeout_ms integer DEFAULT NULL::integer, throw_on_error boolean DEFAULT true, max_attempts integer DEFAULT 1, retry_delay_ms integer DEFAULT 1000
 Type        | func
```

`inference()` 関数は、トレーニング済みの機械学習モデルを使用して、新しい未知のデータに基づいて出力を予測または生成します。

エンドポイントとキーを指定することで、Azure OpenAI と Azure AI Services のエンドポイントに接続したのと同じように、Azure ML でデプロイされたエンドポイントに接続できます。Azure ML を操作するには、トレーニング済みでデプロイされたモデルが必要なため、この演習の範囲外であり、ここで試すためにその接続を設定していません。

## クリーンアップ

この演習を完了したら、作成した Azure リソースを削除します。データベースの使用量ではなく、構成された容量に対して課金されます。次の手順に従って、リソース グループと、このラボ用に作成したすべてのリソースを削除します。
> [!NOTE]
> このラーニング パスで追加のモジュールを完了する予定がある場合は、完了する予定のすべてのモジュールを完了するまで、このタスクをスキップできます。

1. Web ブラウザーを開いて (Azure portal)[https://portal.azure.com/] に移動し、ホームページで Azure サービスの\[**リソースグループ**\]を選択します。

![Select RG](12-azure-portal-home-azure-services-resource-groups.png)

2. 任意のフィールドの検索ボックスに、このラボ用に作成したリソースグループの名前を入力し、一覧からリソースグループを選択します。

3. リソースグループの\[**概要**\]ページで、\[**リソース グループの削除**\]を選択します。

![Delete RG](12-resource-group-delete.png)

4. 確認ダイアログで、削除するリソース グループ名を入力して確認し、\[**削除**\]を選択します。
