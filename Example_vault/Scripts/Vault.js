class Vault {

    async ensureFolder(folder) {

    const parts = folder.split("/");

    let current = "";

    for (const part of parts) {

        current = current ? `${current}/${part}` : part;

        if (!app.vault.getAbstractFileByPath(current)) {
            await app.vault.createFolder(current);
        }

    }

}

    async createNote(folder, name, content) {

        //await this.ensureFolder(folder);

        const path = `${folder}/${name}.md`;
        console.log(path);
        console.log(app.vault.getAbstractFileByPath(path));
        const file = app.vault.getAbstractFileByPath(path);
        if(!file){
            console.log(`Creating new file: ${path}`);
        }
        try{

            return await app.vault.create(path, content);

        }catch(e){
            console.log(`Failed to create file: ${path} modifying it instead`);
        
        try{
            await app.vault.modify(file, content);
        }catch(e){
        console.log(`Failed to modify file: ${path}`, e);
            // console.error(`Failed to modify file: ${path}`, e);
        }
        return file;
    
}

}
    async open(path) {
        const file = app.vault.getAbstractFileByPath(path);
        if(file)
            app.workspace.getLeaf(true).openFile(file);
    }
    async writeJson(path, object) {

        const folder = path.substring(0, path.lastIndexOf("/"));

        await this.ensureFolder(folder);

        const json = JSON.stringify(object, null, 2);

        const file = app.vault.getAbstractFileByPath(path);

        if (file) {
            await app.vault.modify(file, json);
            return file;
        }

        return await app.vault.create(path, json);
    }

    async readJson(path) {

        const file = app.vault.getAbstractFileByPath(path);

        if (!file)
            return null;

        const text = await app.vault.read(file);

        return JSON.parse(text);
    }

    async nextId(prefix, folder, type) {

        let max = 0;

        const files = app.vault.getMarkdownFiles();

        for (const f of files) {

            if (!f.path.startsWith(folder + "/"))
                continue;

            const cache = app.metadataCache.getFileCache(f);
            const fm = cache && cache.frontmatter;

            if (fm && fm.type === type &&
                typeof fm.id === "string" && fm.id.startsWith(prefix)) {

                const n = parseInt(fm.id.slice(prefix.length), 10);

                if (!isNaN(n) && n > max)
                    max = n;
            }
        }

        return `${prefix}${max + 1}`;
    }
}
